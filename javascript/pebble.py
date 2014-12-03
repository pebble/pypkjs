__author__ = 'katharine'

import PyV8 as v8
import events

from pebblecomm.pebble import Pebble as PebbleComm


class Pebble(events.EventSourceMixin, v8.JSClass):
    def __init__(self, runtime, server):
        self._pebble = PebbleComm()
        self._server = server
        super(Pebble, self).__init__(runtime)

    def _connect(self):
        self._pebble.connect_via_qemu(self._server)
        self._ready()

    def _disconnect(self):
        self._pebble.disconnect()

    def _ready(self):
        self.triggerEvent("ready")

    def sendAppMessage(self, message, success=None, failure=None):
        to_send = {}

        for k in message.keys():
            try:
                int_k = int(k)
                to_send[int_k] = message[str(k)]
            except ValueError:
                #TODO: implement appinfo lookup.
                raise Exception("Unknown message key '%s'" % k)

        #TODO: implement sending.
        if failure is not None:
            failure()

    def showSimpleNotificationOnPebble(self, title, message):
        self._pebble.notification_sms(title, message)

    def getAccountToken(self):
        return "0123456789abcdef0123456789abcdef"

    def getWatchToken(self):
        return "0123456789abcdef0123456789abcdef"
