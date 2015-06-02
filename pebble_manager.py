__author__ = 'katharine'

import logging
import re
import struct
from uuid import UUID

from pebblecomm import Pebble
from timeline.blobdb import BlobDB

logger = logging.getLogger("pypkjs.pebble_manager")


class PebbleManager(object):
    def __init__(self, qemu):
        self.qemu = qemu
        self.pebble = Pebble()
        self.handle_start = None
        self.handle_stop = None
        self.blobdb = None
        self.watch_version_info = None
        self.watch_fw_version = None

    def connect(self):
        self.register_endpoints()
        self.pebble.connect_via_qemu(self.qemu)
        self.pebble.emu_bluetooth_connection(True)
        self.determine_version_info()
        self.blobdb = BlobDB(self.pebble)
        self.blobdb.run()
        self.request_running_app()
        logger.info('connected to %s', self.qemu)

    def disconnect(self):
        self.pebble.disconnect()

    def register_endpoints(self):
        self.pebble.register_endpoint("APPLICATION_LIFECYCLE", self.handle_lifecycle, preprocess=False)
        self.pebble.register_endpoint("LAUNCHER", self.handle_launcher, preprocess=False)

    def determine_version_info(self):
        self.watch_version_info = self.pebble.get_versions()
        
        version_str = self.watch_version_info['normal_fw']['version'][1:]
        pieces = re.split(r"[.-]", version_str)
        self.watch_fw_version = [int(pieces[0]), int(pieces[1])] 
    
    def request_running_app(self):
        # This is an appmessage with a null UUID and dictionary {2: 1} with a uint8 value.
        self.pebble._send_message("LAUNCHER", "\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x00\x00\x00\x02\x01\x00\x01")

    def handle_lifecycle(self, endpoint, data):
        state, = struct.unpack_from('<B', data, 0)
        uuid = UUID(bytes=data[1:])
        logger.debug("received lifecycle message for %s: %s", uuid, state)
        if state == 0x01:  # running
            if callable(self.handle_start):
                self.handle_start(uuid)
        elif state == 0x02:  # not running
            if callable(self.handle_stop):
                self.handle_stop(uuid)

    def handle_launcher(self, endpoint, data):
        # World's laziest appmessage parser
        if data[0] != '\x01':  # ignore anything other than pushed data.
            return
        uuid = UUID(bytes=data[2:18])
        state, = struct.unpack('<B', data[26])
        # we should ack it
        self.pebble._send_message("LAUNCHER", "\xff" + data[1])
        if state == 0x01:  # running
            if callable(self.handle_start):
                self.handle_start(uuid)
        elif state == 0x00:  # not running
            if callable(self.handle_stop):
                self.handle_stop(uuid)
    
    @property
    def timeline_is_supported(self):
        return self.watch_fw_version[0] >= 3

