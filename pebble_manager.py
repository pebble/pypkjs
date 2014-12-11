__author__ = 'katharine'

import struct
from uuid import UUID

from pebblecomm import Pebble


class PebbleManager(object):
    def __init__(self, qemu):
        self.qemu = qemu
        self.pebble = Pebble()
        self.handle_start = None
        self.handle_stop = None

    def connect(self):
        self.register_endpoints()
        self.pebble.connect_via_qemu(self.qemu)
        print 'connected to %s' % self.qemu

    def disconnect(self):
        self.pebble.disconnect()

    def register_endpoints(self):
        self.pebble.register_endpoint("APPLICATION_LIFECYCLE", self.handle_lifecycle)
        self.pebble.register_endpoint("LAUNCHER", self.handle_launcher)

    def handle_lifecycle(self, endpoint, data):
        state, = struct.unpack_from('<B', data, 0)
        uuid = UUID(bytes=data[1:])
        print "received lifecycle message for %s: %s" % (uuid, state)
        if state == 0x01:  # running
            if callable(self.handle_start):
                self.handle_start(uuid)
        elif state == 0x02:  # not running
            if callable(self.handle_stop):
                self.handle_stop(uuid)

    def handle_launcher(self, endpoint, data):
        # World's laziest appmessage parser
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
