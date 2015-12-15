from __future__ import absolute_import
__author__ = 'katharine'

import gevent
import logging
import uuid

from libpebble2.communication import PebbleConnection
from libpebble2.communication.transports.qemu import QemuTransport, MessageTargetQemu
from libpebble2.communication.transports.qemu.protocol import QemuBluetoothConnection
from libpebble2.protocol.apps import *
from libpebble2.protocol.legacy2 import LegacyAppLaunchMessage
from libpebble2.services.appmessage import AppMessageService, Uint8
from libpebble2.services.blobdb import BlobDBClient

logger = logging.getLogger("pypkjs.pebble_manager")


class PebbleManager(object):
    def __init__(self, qemu):
        self.qemu = qemu.split(':')
        print self.qemu
        self.pebble = PebbleConnection(QemuTransport(*self.qemu), log_packet_level=logging.DEBUG)
        self.handle_start = None
        self.handle_stop = None
        self.blobdb = None
        self.launcher = None

    def connect(self):
        self.pebble.connect()
        greenlet = gevent.spawn(self.pebble.run_sync)
        self.pebble.fetch_watch_info()
        self.register_endpoints()
        self.pebble.transport.send_packet(QemuBluetoothConnection(connected=True), target=MessageTargetQemu())
        self.blobdb = BlobDBClient(self.pebble)
        self.request_running_app()
        logger.info('connected to %s', self.qemu)
        return greenlet

    def disconnect(self):
        if self.launcher is not None:
            self.launcher.shutdown()

    def register_endpoints(self):
        self.pebble.register_endpoint(AppRunState, self.handle_lifecycle)
        self.launcher = AppMessageService(self.pebble, message_type=LegacyAppLaunchMessage)
        self.launcher.register_handler("appmessage", self.handle_launcher)
    
    def request_running_app(self):
        if self.pebble.firmware_version.major >= 3:
            self.pebble.send_packet(AppRunState(data=AppRunStateRequest()))
        else:
            self.launcher.send_message(uuid.UUID(int=0), {LegacyAppLaunchMessage.Keys.StateFetch: Uint8(1)})

    def handle_lifecycle(self, packet):
        if isinstance(packet.data, AppRunStateStart):
            if callable(self.handle_start):
                self.handle_start(packet.data.uuid)
        elif isinstance(packet.data, AppRunStateStop):
            if callable(self.handle_stop):
                self.handle_stop(packet.data.uuid)

    def handle_launcher(self, txid, uuid, message):
        state = message[LegacyAppLaunchMessage.Keys.RunState]
        if state == LegacyAppLaunchMessage.States.Running:
            if callable(self.handle_start):
                self.handle_start(uuid)
        elif state == LegacyAppLaunchMessage.States.NotRunning:
            if callable(self.handle_stop):
                self.handle_stop(uuid)
    
    @property
    def timeline_is_supported(self):
        return self.pebble.firmware_version.major >= 3

