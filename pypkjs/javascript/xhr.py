from __future__ import absolute_import
__author__ = 'katharine'

from gevent import monkey; monkey.patch_all()

import requests
import requests.exceptions

import pypkjs.PyV8 as v8
from . import events
from .safe_requests import NonlocalHTTPAdapter
from .exceptions import JSRuntimeException

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
    native function _xhr();
    this.XMLHttpRequest = function() {
        var origin = new _xhr(runtime, session);
        _make_proxies(this, origin, ['open', 'setRequestHeader', 'overrideMimeType', 'send', 'getResponseHeader',
                                        'getAllResponseHeaders', 'abort', 'addEventListener', 'removeEventListener']);
        _make_properties(this, origin, ['readyState', 'response', 'responseText', 'responseType', 'status',
                                        'statusText', 'timeout', 'onreadystatechange', 'ontimeout', 'onload',
                                        'onloadstart', 'onloadend', 'onprogress', 'onerror', 'onabort']);
    }
    this.XMLHttpRequest.UNSENT = 0;
    this.XMLHttpRequest.OPENED = 1;
    this.XMLHttpRequest.HEADERS_RECEIVED = 2;
    this.XMLHttpRequest.LOADING = 3;
    this.XMLHttpRequest.DONE = 4;

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
        self._request = None
        self._response = None
        self._async = False
        self._mime_override = None
        self._runtime = runtime
        self._session = session
        self._thread = None
        self._sent = False

        super(XMLHttpRequest, self).__init__(runtime)


    def open(self, method, url, async=True, user=None, password=None):
        self._request = requests.Request(method, url)
        if user is not None:
            self._request.auth = (user, password or "")
        self._async = async
        self.readyState = self.OPENED
        self._trigger_async_event("readystatechange")

    def setRequestHeader(self, header, value):
        if self.readyState != self.OPENED:
            raise JSRuntimeException("Request headers can only be set in the OPENED state.")
        if self._sent:
            raise JSRuntimeException("Request headers cannot be set after sending a request.")
        self._request.headers[header] = value

    def overrideMimeType(self, mimetype):
        if self.readyState >= self.LOADING:
            raise JSRuntimeException("The mime type cannot be overridden after the request starts loading.")
        self._mime_override = mimetype

    def _do_request_error(self, exception, event):
        self.readyState = self.DONE
        if not self._async:
            raise Exception(exception)
        self._trigger_async_event("readystatechange")

    def _do_send(self):
        self._sent = True
        req = self._session.prepare_request(self._request)
        try:
            if self.timeout:
                timeout = self.timeout / 1000.0
            else:
                timeout = None
            self._response = self._session.send(req, timeout=timeout, verify=True)
            self.readyState = self.DONE
            self.status = self._response.status_code
            self.statusText = self._response.reason
            self.responseText = self._response.text

            if self.responseType == "json":
                self.response = self._response.json()
            elif self.responseType == "arraybuffer":
                self.response = v8.JSObject.create(self._runtime.context.locals.Uint8Array, (v8.JSArray(list(bytearray(self._response.content))),)).buffer
            else:
                self.response = self.responseText

            self._trigger_async_event("load", ProgressEvent, (self._runtime,))
        except requests.exceptions.Timeout:
            self._trigger_async_event("timeout", ProgressEvent, (self._runtime,))
            self.readyState = self.DONE
        except requests.exceptions.RequestException as e:
            self.status = 0
            self.statusText = str(e)
            self.readyState = self.DONE
        finally:
            self._trigger_async_event("loadend", ProgressEvent, (self._runtime,))
            self._trigger_async_event("readystatechange")

    def _trigger_async_event(self, event_name, event=None, event_params=(), params=()):
        def go():
            if event is not None:
                self.triggerEvent(event_name, event(*event_params), *params)
            else:
                self.triggerEvent(event_name, *params)
        if self._async:
            go()
        else:
            self._runtime.enqueue(go)

    def send(self, data=None):
        if data is not None:
            if not isinstance(data, basestring) and str(data) == '[object ArrayBuffer]':
                uint8_array = self._runtime.context.locals.Uint8Array
                data_array = uint8_array.create(uint8_array, (data,))
                self._request.data = bytes(bytearray(data_array[str(x)] for x in xrange(data_array.length)))
            else:
                self._request.data = str(data)
        self._thread = self._runtime.group.spawn(self._do_send)
        if not self._async:
            self._thread.join()

    def getResponseHeader(self, header):
        if self._response is not None:
            return self._response.headers.get(header, None)
        else:
            return None

    def getAllResponseHeaders(self):
        if self._response is None:
            return None
        # https://xhr.spec.whatwg.org/#the-getallresponseheaders()-method
        return '\x0d\x0a'.join('%s\x3a\x20%s' % (k, v) for k, v in self._response.headers.iteritems())

    def abort(self):
        if self._sent and self._thread is not None:
            self._thread.kill(block=False)


def prepare_xhr(runtime):
    session = requests.Session()
    if runtime.block_private_addresses:
        adapter = NonlocalHTTPAdapter()
        session.mount('http://', adapter)
        session.mount('https://', adapter)
    return runtime.context.locals._init_xhr(runtime, session)
