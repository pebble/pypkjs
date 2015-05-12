__author__ = 'katharine'

import gevent
import json
import logging
import requests
import struct
import uuid

from blobdb import BlobDB
from model import TimelineItem, TimelineActionSet
from attributes import TimelineAttributeSet


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
            self.send_result(item_id, False, attributes={
                'subtitle': 'Failed',
                'largeIcon': 'system://images/RESULT_FAILED',
            })
            self.logger.warn("Discarded unknown action.")
            return

        self.logger.debug("action: %s", action)

        action_handlers = {
            'http': self.handle_http,
            'remove': self.handle_remove,
            'dismiss': self.handle_dismiss,
        }
        if action['type'] in action_handlers:
            try:
                result = action_handlers[action['type']](item, action)
                if result is not None:
                    self.send_result(item_id, *result)
            except Exception as e:
                import traceback
                traceback.print_exc()
                logging.warning("Something broke: %s", e)
                self.send_result(item_id, False, {'subtitle': 'Failed', 'largeIcon': 'system://images/RESULT_SENT'})
        else:
           self.send_result(item_id, False, {'subtitle': 'Not Implemented', 'largeIcon': 'system://images/RESULT_FAILED'})

    def handle_remove(self, item, action):
        item.deleted = True
        item.save()
        self.pebble.blobdb.delete(BlobDB.DB_PIN, item.uuid)
        for child in TimelineItem.select().where((TimelineItem.parent == item.uuid) & (TimelineItem.type == 'notification')):
            self.pebble.blobdb.delete(BlobDB.DB_NOTIFICATION, child.uuid)
            child.deleted = True
            child.save()
        return True, {'subtitle': 'Removed', 'largeIcon': 'system://images/RESULT_DELETED'}

    def handle_http(self, item, action):
        def go():
            url = action['url']
            method = action.get('method', 'POST')
            headers = {
                'X-Pebble-Account-Token': self.timeline.runner.account_token,
                'X-Pebble-Watch-Token': self.timeline.runner.watch_token,
            }
            if 'bodyJSON' in action:
                body = json.dumps(action['bodyJSON'])
                headers['Content-Type'] = 'application/json'
            else:
                body = action.get('body', None)

            # We set these last, to give the developer the chance to overwrite our headers.
            headers.update(action.get('headers', {}))

            try:
                response = requests.request(method, url, headers=headers, data=body, allow_redirects=True, timeout=2.5)
                response.raise_for_status()
            except requests.RequestException as e:
                logging.warning("HTTP request failed: %s", e.message)
                self.send_result(item.uuid, False, {'subtitle': "Failed", 'largeIcon': 'system://images/RESULT_FAILED'})
            else:
                logging.info("HTTP request succeeded.")
                self.send_result(item.uuid, True, {})

        gevent.spawn(go)

    def handle_dismiss(self, item, action):
        # We don't actually have to do anything for 'dismiss' actions, but the watch expects us to ACK.
        return True, {'subtitle': 'Dismissed', 'largeIcon': 'system://images/RESULT_DISMISSED'}

    def send_result(self, item_id, success, attributes=None):
        self.logger.info("%sing %s action.", "ACK" if success else "NACK", item_id)
        if attributes is None:
            attributes = {}
        attribute_set = TimelineAttributeSet(attributes, self.timeline.fw_map)
        attribute_count, serialised = attribute_set.serialise()
        response = struct.pack(
            "<B16sBB",
            0x11,
            uuid.UUID(item_id).bytes,
            int(not success),
            attribute_count
        ) + serialised
        self.logger.debug("Serialised action response: %s", response.encode('hex'))
        self.pebble.pebble._send_message("TIMELINE_ACTION", response)
