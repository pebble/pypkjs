__author__ = 'katharine'

import PyV8 as v8


class Event(v8.JSClass):
    NONE = 0
    CAPTURING_PHASE = 1
    AT_TARGET = 2
    BUBBLING_PHASE = 3

    def __init__(self, event_type, event_init_dict=None):
        event_init_dict = event_init_dict or {}
        self.type = event_type
        self.bubbles = event_init_dict.get('bubbles', False)
        self.cancelable = event_init_dict.get('cancelable', False)
        self.defaultPrevented = False
        self.target = None
        self.currentTarget = None
        self.eventPhase = self.AT_TARGET  # Neither capturing nor bubbling exist, so...

        self._aborted = False

    def stopPropagation(self):
        pass

    def stopImmediatePropagation(self):
        self._aborted = True

    def preventDefault(self):
        self.defaultPrevented = True

    def initEvent(self, event_type, bubbles, cancelable):
        self.type = event_type
        self.bubbles = bubbles
        self.cancelable = cancelable


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

    def triggerEvent(self, event_name, event=None, *params):
        if event is None:
            event = Event(event_name)
        for listener in self._listeners.get(event_name, []):
            try:
                listener.call(self, event, *params)
            except v8.JSError as e:
                pass  #TODO: Figure out how to report these
            finally:
                if event._aborted:
                    break

        #TODO: Figure out if these come before or after addEventListener handlers.
        try:
            dom_event = self.__getattribute__("on" + event_name)
        except AttributeError:
            pass
        else:
            try:
                if dom_event is not None:
                    dom_event.call(self, event, *params)
            except v8.JSError as e:
                pass  #TODO: error handling again
