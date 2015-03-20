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
        item = TimelineItem.get(TimelineItem.uuid == item_id)
        actions = TimelineActionSet(item)
        action = actions.get_actions()[action_id]
        self.logger.debug("action: %s", action)

        action_handlers = {
            'remove': self.handle_remove,
            # 'mute': self.handle_mute,
        }
        if action['type'] in action_handlers:
            action_handlers[action['type']](item)

    def handle_remove(self, item):
        item.deleted = True
        item.save()
        self.pebble.blobdb.delete(BlobDB.DB_PIN, item.uuid)
        for child in TimelineItem.select().where((TimelineItem.parent == item.uuid) & (TimelineItem.type == 'notification')):
            self.pebble.blobdb.delete(BlobDB.DB_NOTIFICATION, child.uuid)
            child.deleted = True
            child.save()
