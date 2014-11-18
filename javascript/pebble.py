__author__ = 'katharine'

import PyV8 as v8


class Pebble(v8.JSClass):
    def __init__(self):
        self._listeners = {}

    def _ready(self):
        for listener in self._listeners.get("ready", []):
            listener()

    def addEventListener(self, event, listener, capture=False):
        self._listeners.setdefault(event, []).append(listener)

    def removeEventListener(self, event, listener=None):
        if event not in self._listeners:
            return
        if listener is None:
            del self._listeners[event]
        else:
            for i, listener_i in enumerate(self._listeners[event]):
                if listener_i == listener:
                    del listener[i]
                    break

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
