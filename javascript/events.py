__author__ = 'katharine'

import PyV8 as v8


class EventSourceMixin(object):
    def __init__(self):
        self._listeners = {}
        super(EventSourceMixin, self).__init__()

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

    def triggerEvent(self, event, *params):
        for listener in self._listeners.get(event, []):
            try:
                listener(*params)
            except v8.JSError as e:
                pass  #TODO: Figure out how to report these
