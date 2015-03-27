__author__ = 'katharine'

import gevent
import json
import logging
import requests
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
        item = TimelineItem.get(TimelineItem.uuid == item_id)
        actions = TimelineActionSet(item)
        action = actions.get_actions()[action_id]
        self.logger.debug("action: %s", action)

        action_handlers = {
            'http': self.handle_http,
            'remove': self.handle_remove,
            # 'mute': self.handle_mute,
        }
        if action['type'] in action_handlers:
            action_handlers[action['type']](item, action)

    def handle_remove(self, item, action):
        item.deleted = True
        item.save()
        self.pebble.blobdb.delete(BlobDB.DB_PIN, item.uuid)
        for child in TimelineItem.select().where((TimelineItem.parent == item.uuid) & (TimelineItem.type == 'notification')):
            self.pebble.blobdb.delete(BlobDB.DB_NOTIFICATION, child.uuid)
            child.deleted = True
            child.save()

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
