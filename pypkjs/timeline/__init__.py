from __future__ import absolute_import
__author__ = 'katharine'

import datetime
from dateutil.tz import tzlocal
import gevent
import json
import logging
import os
import traceback
import uuid

from libpebble2.protocol.blobdb import *

from .actions import ActionHandler
from . import model
from .model import TimelineItem, TimelineState, TimelineSubscription, PinTopic
from .websync import TimelineWebSync


class PebbleTimeline(object):
    def __init__(self, runner, oauth=None, persist=None, layout_file=None):
        self.runner = runner
        self.logger = self.runner.logger.getChild('timeline')
        self.oauth = oauth
        self.persist_dir = persist
        self.map_url = self.runner.urls.fw_resource_map
        self.action_handler = ActionHandler(self, self.runner.pebble)
        self._fw_map_cache = None
        self._layout_file_path = layout_file
        self._pending_sends = set()
        if persist is not None:
            model.prepare_db(self.persist_dir + '/timeline.db')
        else:
            model.prepare_db(':memory:')

    @property
    def fw_map(self):
        if self._fw_map_cache is None:
            if self._layout_file_path is not None:
                with open(self._layout_file_path) as f:
                    self._fw_map_cache = json.load(f)
            else:
                with open(os.path.join(os.path.dirname(__file__), 'layouts.json')) as f:
                    self._fw_map_cache = json.load(f)
        return self._fw_map_cache

    def perform_sync(self):
        sync = TimelineWebSync(self.runner.urls, self.oauth)
        for type, pin in sync.update_iter():
            try:
                self.handle_update(type, pin)
            except (gevent.GreenletExit, KeyboardInterrupt):
                raise
            except Exception:
                traceback.print_exc()
                self.logger.warning("Skipped invalid pin %s.", pin)

    def _continuous_sync(self):
        while True:
            self.perform_sync()
            gevent.sleep(15)

    def continuous_sync(self):
        if self.oauth is not None:
            gevent.spawn(self._continuous_sync)
        else:
            self.logger.error("Web sync disabled; no oauth token.")

    def handle_update(self, update_type, pin):
        update_handlers = {
            'sync.resync': self.handle_resync,
            'timeline.pin.create': self.handle_pin_create,
            'timeline.pin.delete': self.handle_pin_delete,
            'timeline.topic.subscribe': self.handle_subscribe,
            'timeline.topic.unsubscribe': self.handle_unsubscribe,
        }

        self.logger.info("handling %s update", update_type)
        if update_type in update_handlers:
            update_handlers[update_type](pin)

    def handle_resync(self, pin):
        for item in TimelineItem.select().where(TimelineItem.source_kind == 'web'):
            with model.db.atomic():
                item_id = item.uuid
                item.delete_instance(recursive=True)
                if item.has_sent:
                    self.runner.pebble.blobdb.delete(uuid.UUID(item_id))

    def handle_pin_create(self, pin, manual=False):
        pin_item = TimelineItem.from_web_pin(pin)

        ignored_level = logging.DEBUG if not manual else logging.WARNING

        is_updating = pin_item.exists()
        if is_updating:
            old_pin = TimelineItem.get(TimelineItem.uuid == pin_item.uuid)
            if old_pin.deleted:
                self.logger.log(ignored_level, "Pin was already deleted; ignoring.")
                return

            if old_pin.updated >= pin_item.updated:
                # Even if nothing's changed, as long as the pin's not older we should update topics.
                if pin_item.updated >= old_pin.updated:
                    self.logger.debug("updating topics.")
                    old_pin.update_topics(pin['topicKeys'])
                self.logger.log(ignored_level, "Nothing's changed; ignoring.")
                return

            self.logger.debug("uuid already exists; removing old reminders.")
            # We delete every reminder because we need to update them, but can't tell which ones are updated.
            # This is okay as long as we don't reinsert reminders that already passed.
            for reminder in TimelineItem.select().where((TimelineItem.parent == pin_item.uuid) & (TimelineItem.type == 'reminder')):
                if reminder.has_sent:
                    self.runner.pebble.blobdb.delete(BlobDatabaseID.Reminder, uuid.UUID(reminder.uuid))
                reminder.delete_instance()

        next_notification = pin_item.get_notification_to_display(pin, preexisting=pin_item.exists())
        self.logger.debug("next notification: %s", next_notification)
        reminders = pin_item.make_reminders(pin.get('reminders', []))
        self.logger.debug("reminders: %s", reminders)

        pin_item.save(force_insert=not pin_item.exists())
        pin_item.update_topics(pin['topicKeys'])
        self.logger.debug("saved pin")
        if next_notification is not None:
            if is_updating:
                TimelineItem.delete().where((TimelineItem.type == 'notification') &
                                            (TimelineItem.parent == pin_item.uuid)).execute()
            next_notification.save(force_insert=True)
            self._send(next_notification)
        for reminder in reminders:
            reminder.save(force_insert=True)
            self._send(reminder)
        self._send(pin_item)

    def handle_pin_delete(self, pin):
        types = {
            'pin': BlobDatabaseID.Pin,
            'notification': BlobDatabaseID.Notification,
            'reminder': BlobDatabaseID.Reminder,
        }

        pin_uuid = pin['guid']
        try:
            pin = TimelineItem.get(TimelineItem.uuid == pin_uuid)
        except TimelineItem.DoesNotExist:
            return
        self.runner.pebble.blobdb.delete(BlobDatabaseID.Pin, uuid.UUID(pin_uuid))
        pin.deleted = True
        pin.save()
        for child in pin.children:
            self.runner.pebble.blobdb.delete(types[child.type], uuid.UUID(pin_uuid))
            child.deleted = True
            child.save()

    def handle_subscribe(self, topic):
        topic_key = topic['topicKey']
        TimelineSubscription.subscribe(topic_key)

    def handle_unsubscribe(self, topic):
        topic_key = topic['topicKey']
        TimelineSubscription.unsubscribe(topic_key)
        with model.db.atomic():
            defunct_pins = PinTopic.pins_with_only(topic_key)
            for pin_id in defunct_pins:
                try:
                    pin = TimelineItem.get(TimelineItem.uuid == pin_id)
                except TimelineItem.DoesNotExist:
                    self.logger.error("Inconsistency error; failed to find pin that should exist.")
                else:
                    if pin.has_sent and not pin.deleted:
                        self.runner.pebble.blobdb.delete(BlobDatabaseID.Pin, uuid.UUID(pin_id))

                for reminder in TimelineItem.select().where((TimelineItem.parent == pin_id) & (TimelineItem.type == 'reminder')):
                    if reminder.has_sent and not reminder.deleted:
                        self.runner.pebble.blobdb.delete(BlobDatabaseID.Reminder, uuid.UUID(reminder.uuid))

                TimelineItem.delete().where((TimelineItem.uuid == pin_id) | (TimelineItem.parent == pin_id)).execute()
            TimelineSubscription.delete().where(TimelineSubscription.topic == topic_key).execute()
            # This should be caught by ON DELETE CASCADE - but the ancient sqlite3 version we have doesn't support that.
            PinTopic.delete().where(PinTopic.topic == topic_key).execute()

    def _window_start(self):
        now = datetime.datetime.now(tz=tzlocal())
        today = datetime.datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
        yesterday = today - datetime.timedelta(days=1)
        return yesterday

    def _window_end(self):
        distant_future = self._window_start() + datetime.timedelta(days=4)
        return distant_future

    def _send(self, item):
        types = {
            'pin': BlobDatabaseID.Pin,
            'notification': BlobDatabaseID.Notification,
            'reminder': BlobDatabaseID.Reminder,
        }

        if not item.sendable:
            return

        item.has_sent = False
        item.rejected = False
        item.save(only=(TimelineItem.has_sent, TimelineItem.rejected))

        in_range = (self._window_start() <= item.start_time < self._window_end() or
                    TimelineItem.select().where(
                        TimelineItem.start_time.between(self._window_start(), self._window_end())
                        & (TimelineItem.parent == item.uuid)).exists())


        if in_range:
            self.logger.info("in watch range; inserting.")
            self._pending_sends.add(item.uuid)
            try:
                serialised = item.serialise(self)
            except:
                traceback.print_exc()
                self.logger.error("Serialisation of timeline item failed.")
                item.rejected = True
                item.save(only=[TimelineItem.rejected])
                return
            self.runner.pebble.blobdb.insert(types[item.type], uuid.UUID(item.uuid), serialised, lambda x: self._did_send(item, x))

    def _do_maintenance(self):
        while True:
            self.logger.debug("Running maintenance process.")
            # Delete old timeline items predating the window.
            TimelineItem.delete().where(TimelineItem.start_time < self._window_start()).execute()
            # Send timeline items that are now in the end of our window.
            for item in TimelineItem.select().where(
                            (TimelineItem.start_time < self._window_end())
                            & (TimelineItem.has_sent == False)
                            & (TimelineItem.rejected == False)
                            & (TimelineItem.sendable == True)):
                if item.uuid in self._pending_sends:
                    continue
                self.logger.debug("Got pending item %s", item.uuid)
                try:
                    parent = TimelineItem.get((TimelineItem.uuid == item.parent) & (TimelineItem.has_sent == False)
                                              & (TimelineItem.rejected == False) & (TimelineItem.sendable == True))
                except TimelineItem.DoesNotExist:
                    pass
                else:
                    self.logger.debug("Sending parent, too.")
                    self._send(parent)
                self._send(item)
            gevent.sleep(600)

    def do_maintenance(self):
        gevent.spawn(self._do_maintenance)

    def _did_send(self, item, status):
        self.logger.debug("got result for item %s", item)

        try:
            self._pending_sends.remove(item.uuid)
        except KeyError:
            pass

        if status == 1:
            self.logger.debug("insert successful.")
            item.has_sent = True
            item.save(only=[TimelineItem.has_sent])
        else:
            self.logger.warning("Timeline item insert failed: %s", status)
            item.rejected = True
            item.save(only=[TimelineItem.rejected])
