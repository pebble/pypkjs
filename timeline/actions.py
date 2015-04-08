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
                'subtitle': 'Failed.',
                'largeIcon': 'system://images/TIMELINE_SENT_LARGE',
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
            action_handlers[action['type']](item, action)
            success, attributes = action_handlers[action['type']](item, action)
        else:
            success, attributes = False, {'subtitle': 'Not Implemented', 'largeIcon': 'system://images/TIMELINE_SENT_LARGE'}
        self.send_result(item_id, success, attributes)

    def handle_remove(self, item, action):
        item.deleted = True
        item.save()
        self.pebble.blobdb.delete(BlobDB.DB_PIN, item.uuid)
        for child in TimelineItem.select().where((TimelineItem.parent == item.uuid) & (TimelineItem.type == 'notification')):
            self.pebble.blobdb.delete(BlobDB.DB_NOTIFICATION, child.uuid)
            child.deleted = True
            child.save()
        return True, {'subtitle': 'Removed', 'largeIcon': 'system://images/TIMELINE_SENT_LARGE'}

    def handle_http(self, item, action):
        url = action['url']
        method = action.get('method', 'POST')
        headers = action.get('headers', {})
        if 'bodyJSON' in action:
            body = json.dumps(action['bodyJSON'])
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
        else:
            body = action.get('body', None)
        gevent.spawn(requests.request, method, url, headers=headers, data=body)

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

    def handle_dismiss(self, item):
        # We don't actually have to do anything for 'dismiss' actions, but the watch expects us to ACK.
        return True, {'subtitle': 'Dismissed', 'largeIcon': 'system://images/TIMELINE_SENT_LARGE'}
