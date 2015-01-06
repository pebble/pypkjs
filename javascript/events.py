__author__ = 'katharine'

import PyV8 as v8

from javascript.exceptions import JSRuntimeException

event = v8.JSExtension("runtime/event", """
    Event = function(event_type, event_init_dict) {
        var self = this;
        this.stopPropagation = function() {};
        this.stopImmediatePropagation = function() { self._aborted = true; }
        this.preventDefault = function() { self.defaultPrevented = true; }
        this.initEvent = function(event_type, bubbles, cancelable) {
            self.type = event_type;
            self.bubbles = bubbles;
            self.cancelable = cancelable
        };
        if(!event_init_dict) event_init_dict = {};

        this.type = event_type;
        this.bubbles = event_init_dict.bubbles || false;
        this.cancelable = event_init_dict.cancelable || false;
        this.defaultPrevented = false;
        this.target = null;
        this.currentTarget = null;
        this.eventPhase = 2;
        this._aborted = false;
    };
    Event.NONE = 0;
    Event.CAPTURING_PHASE = 1;
    Event.AT_TARGET = 2;
    Event.BUBBLING_PHASE = 3;
""")

Event = lambda runtime, *args: v8.JSObject.create(runtime.context.locals.Event, args)

class EventSourceMixin(object):
    def __init__(self, runtime):
        self._listeners = {}
        self._runtime = runtime
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
            event = Event(self._runtime, event_name)

        def go():
            for listener in self._listeners.get(event_name, []):
                try:
                    listener.call(self, event, *params)
                except Exception as e:
                    self._runtime.log_output(JSRuntimeException(self._runtime, e.message).stackTrace)
                    raise
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
                except Exception as e:
                    self._runtime.log_output(JSRuntimeException(self._runtime, e.message).stackTrace)
                    raise

        self._runtime.enqueue(go)

