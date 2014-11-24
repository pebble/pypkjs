__author__ = 'katharine'

import PyV8 as v8
import events


class Pebble(events.EventSourceMixin, v8.JSClass):
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
        pass

    def getAccountToken(self):
        return "0123456789abcdef0123456789abcdef"

    def getWatchToken(self):
        return "0123456789abcdef0123456789abcdef"
