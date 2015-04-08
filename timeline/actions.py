__author__ = 'katharine'

import logging
import struct
import uuid

from blobdb import BlobDB
from model import TimelineItem, TimelineActionSet


class ActionHandler(object):
    def __init__(self, timeline, pebble):
        self.timeline = timeline
        self.pebble = pebble
        self.logger = logging.getLogger("pypkjs.timeline.actions")
        self.pebble.pebble.register_endpoint('TIMELINE_ACTION', self.handle_action, preprocess=False)

    def handle_action(self, endpoint, message):
        self.logger.debug('handling timeline action')
        command, = struct.unpack('<B', message[0])
        self.logger.debug("command: %s", command)
        # "invoke" is the only message we should ever receive.
        if command != 0x02:
            return

        item_id_bytes, action_id, num_attributes = struct.unpack_from("<16sBB", message, 1)
        item_id = str(uuid.UUID(bytes=item_id_bytes))
        self.logger.debug("item_id: %s, action_id: %s", item_id, action_id)
        try:
            item = TimelineItem.get(TimelineItem.uuid == item_id)
            actions = TimelineActionSet(item)
            action = actions.get_actions()[action_id]
        except (TimelineItem.DoesNotExist, KeyError, IndexError):
            self.send_result(item_id, action_id, False)
            self.logger.warn("Discarded unknown action.")
            return

        self.logger.debug("action: %s", action)

        action_handlers = {
            'remove': self.handle_remove,
            'dismiss': self.handle_dismiss,
            # 'mute': self.handle_mute,
        }
        if action['type'] in action_handlers:
            success = action_handlers[action['type']](item)
        else:
            success = False
        self.send_result(item_id, action_id, success)

    def handle_remove(self, item):
        item.deleted = True
        item.save()
        self.pebble.blobdb.delete(BlobDB.DB_PIN, item.uuid)
        for child in TimelineItem.select().where((TimelineItem.parent == item.uuid) & (TimelineItem.type == 'notification')):
            self.pebble.blobdb.delete(BlobDB.DB_NOTIFICATION, child.uuid)
            child.deleted = True
            child.save()
        return True

    def send_result(self, item_id, action_id, success, subtitle=None, icon=None):
        self.logger.info("%sing (%s, %s).", "ACK" if success else "NACK", item_id, action_id)
        response = struct.pack("<B16sBBB", 0x11, uuid.UUID(item_id).bytes, action_id, int(not success), 0)
        self.pebble.pebble._send_message("TIMELINE_ACTION", response)

    def handle_dismiss(self, item):
        # We don't actually have to do anything for 'dismiss' actions, but the watch expects us to ACK.
        return True
