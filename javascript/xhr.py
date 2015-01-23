__author__ = 'katharine'

from gevent import monkey; monkey.patch_all()
import PyV8 as v8
import requests
import requests.exceptions
import exceptions
import events

progress_event = v8.JSExtension("runtime/events/progress", """
ProgressEvent = function(computable, loaded, total) {
    Event.call(this);
    computable = computable || false;
    loaded = loaded || 0;
    total = total || 0;
    Object.defineProperties(this, {
        lengthComputable: {
            get: function() { return computable; },
            enumerable: true,
        },
        loaded: {
            get: function() { return loaded; },
            enumerable: true,
        },
        total: {
            get: function() { return total; },
            enumerable: true,
        },
    });
}
ProgressEvent.prototype = Object.create(Event.prototype);
ProgressEvent.prototype.constructor = ProgressEvent;
""", dependencies=["runtime/event"])

ProgressEvent = lambda runtime, *args: v8.JSObject.create(runtime.context.locals.ProgressEvent, args)

xml_http_request = v8.JSExtension("runtime/xhr", """
_init_xhr = function(runtime, session) {
    this.XMLHttpRequest = function() {
        native function _xhr();
        var origin = new _xhr(runtime, session);
        _make_proxies(this, origin, ['open', 'setRequestHeader', 'overrideMimeType', 'send', 'getResponseHeader',
                                        'getAllResponseHeaders', 'abort', 'addEventListener', 'removeEventListener']);
        _make_properties(this, origin, ['readyState', 'response', 'responseText', 'responseType', 'status',
                                        'statusText', 'timeout', 'onreadystatechange', 'ontimeout', 'onload',
                                        'onloadstart', 'onloadend', 'onprogress', 'onerror', 'onabort']);
    }
}
""", lambda f: XMLHttpRequest, dependencies=[progress_event.name])


class XMLHttpRequest(events.EventSourceMixin):
    UNSENT = 0
    OPENED = 1
    HEADERS_RECEIVED = 2
    LOADING = 3
    DONE = 4

    def __init__(self, runtime, session):
        # properties
        self.readyState = self.UNSENT
        self.response = None
        self.responseText = None
        self.responseType = ""
        self.status = None
        self.statusText = None
        self.timeout = None

        # handlers
        self.onreadystatechange = None
        self.ontimeout = None
        self.onload = None
        self.onloadstart = None
        self.onloadend = None
        self.onprogress = None
        self.onerror = None
        self.onabort = None

        # internal
        self.__request = None
        self.__async = False
        self.__mime_override = None
        self.__runtime = runtime
        self.__session = session
        self.__thread = None
        self.__sent = False

        super(XMLHttpRequest, self).__init__(runtime)

    def open(self, method, url, async=True, user=None, password=None):
        self.__request = requests.Request(method, url)
        if user is not None:
            self.__request.auth = (user, password or "")
        self.__async = async
        self.readyState = self.OPENED
        self._trigger_async_event("readystatechange")

    def setRequestHeader(self, header, value):
        if self.readyState != self.OPENED:
            raise exceptions.JSRuntimeException("Request headers can only be set in the OPENED state.")
        if self.__sent:
            raise exceptions.JSRuntimeException("Request headers cannot be set after sending a request.")
        self.__request.headers[header] = value

    def overrideMimeType(self, mimetype):
        if self.readyState >= self.LOADING:
            raise exceptions.JSRuntimeException("The mime type cannot be overridden after the request starts loading.")
        self.__mime_override = mimetype

    def _do_request_error(self, exception, event):
        self.readyState = self.DONE
        if not self.__async:
            raise Exception(exception)
        self._trigger_async_event("readystatechange")

    def _do_send(self):
        self.__sent = True
        req = self.__session.prepare_request(self.__request)
        try:
            if self.timeout:
                timeout = self.timeout / 1000.0
            else:
                timeout = None
            resp = self.__session.send(req, timeout=timeout, verify=True)
            self.readyState = self.DONE
            self.status = resp.status_code
            self.statusText = resp.reason
            self.responseText = resp.text

            if self.responseType == "json":
                self.response = resp.json()
            elif self.responseType == "arraybuffer":
                self.response = v8.JSObject.create(self.__runtime.context.locals.Uint8Array, (v8.JSArray(list(bytearray(resp.content))),))
            else:
                self.response = self.responseText

            self._trigger_async_event("load", ProgressEvent, (self._runtime,))
        except requests.exceptions.Timeout:
            self._trigger_async_event("timeout", ProgressEvent, (self._runtime,))
            self.readyState = self.DONE
        except requests.exceptions.RequestException:
            self.readyState = self.DONE
        finally:
            self._trigger_async_event("loadend", ProgressEvent, (self._runtime,))
            self._trigger_async_event("readystatechange")

    def triggerEvent(self, event_name, event=None, *params):
        super(XMLHttpRequest, self).triggerEvent(event_name, event, *params)

    def _trigger_async_event(self, event_name, event=None, event_params=(), params=()):
        def go():
            if event is not None:
                self.triggerEvent(event_name, event(*event_params), *params)
            else:
                self.triggerEvent(event_name, *params)
        if self.__async:
            go()
        else:
            self.__runtime.enqueue(go)

    def send(self, data=None):
        if data is not None:
            self.__request.data = str(data)
        self.__thread = self.__runtime.group.spawn(self._do_send)
        if not self.__async:
            self.__thread.join()

    def getResponseHeader(self, header):
        pass

    def getAllResponseHeaders(self):
        pass

    def abort(self):
        pass


def prepare_xhr(runtime):
    session = requests.Session()
    return runtime.context.locals._init_xhr(runtime, session)
