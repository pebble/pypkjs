__author__ = 'katharine'

import gevent
import logging

from libpebble2.communication import PebbleConnection
from libpebble2.communication.transports.qemu import QemuTransport
from libpebble2.events.threaded import ThreadedEventHandler
from libpebble2.protocol.apps import *
from libpebble2.services.blobdb import BlobDBClient

logger = logging.getLogger("pypkjs.pebble_manager")


class PebbleManager(object):
    def __init__(self, qemu):
        self.qemu = qemu.split(':')
        print self.qemu
        self.pebble = PebbleConnection(QemuTransport(*self.qemu))
        self.handle_start = None
        self.handle_stop = None
        self.blobdb = None

    def connect(self):
        self.pebble.connect()
        thing = gevent.spawn(self._pump_pebble)
        self.register_endpoints()
        # self.pebble.emu_bluetooth_connection(True)
        self.blobdb = BlobDBClient(self.pebble, ThreadedEventHandler)
        self.request_running_app()
        logger.info('connected to %s', self.qemu)
        return thing

    def _pump_pebble(self):
        while True:
            self.pebble.pump_reader()

    def disconnect(self):
        pass

    def register_endpoints(self):
        self.pebble.register_endpoint(AppRunState, self.handle_lifecycle)
        # self.pebble.register_endpoint("LAUNCHER", self.handle_launcher, preprocess=False)
    
    def request_running_app(self):
        self.pebble.send_packet(AppRunState(data=AppRunStateRequest()))

    def handle_lifecycle(self, packet):
        if isinstance(packet.data, AppRunStateStart):
            if callable(self.handle_start):
                self.handle_start(packet.data.uuid)
        elif isinstance(packet.data, AppRunStateStop):
            if callable(self.handle_stop):
                self.handle_stop(packet.data.uuid)

    # def handle_launcher(self, endpoint, data):
    #     # World's laziest appmessage parser
    #     if data[0] != '\x01':  # ignore anything other than pushed data.
    #         return
    #     uuid = UUID(bytes=data[2:18])
    #     state, = struct.unpack('<B', data[26])
    #     # we should ack it
    #     self.pebble._send_message("LAUNCHER", "\xff" + data[1])
    #     if state == 0x01:  # running
    #         if callable(self.handle_start):
    #             self.handle_start(uuid)
    #     elif state == 0x00:  # not running
    #         if callable(self.handle_stop):
    #             self.handle_stop(uuid)
    
    @property
    def timeline_is_supported(self):
        return self.pebble.firmware_version.major >= 3

