__author__ = 'katharine'

from gevent import monkey; monkey.patch_all()
import gevent
import PyV8 as v8
import requests
import requests.exceptions
import events


class ProgressEvent(events.Event):
    def __init__(self, computable=False, loaded=0, total=0):
        self._lengthComputable = computable
        self._loaded = loaded
        self._total = total
        events.Event.__init__(self, "ProgressEvent")

    @property
    def lengthComputable(self):
        return self._lengthComputable

    @property
    def loaded(self):
        return self._loaded

    @property
    def total(self):
        return self._total


class XMLHttpRequest(events.EventSourceMixin, v8.JSClass):
    UNSENT = 0
    OPENED = 1
    HEADERS_RECEIVED = 2
    LOADING = 3
    DONE = 4

    def __init__(self, group, session):
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
        self.__group = group
        self.__session = session
        self.__thread = None

        super(XMLHttpRequest, self).__init__()

    def open(self, method, url, async=True, user=None, password=None):
        self.__request = requests.Request(method, url)
        if user is not None:
            self.__request.auth = (user, password or "")
        self.__async = async
        self.readyState = self.OPENED
        self.triggerEvent("readystatechange")

    def overrideMimeType(self, mimetype):
        self.__mime_override = mimetype

    def _do_request_error(self, exception, event):
        self.readyState = self.DONE
        if not self.__async:
            raise Exception(exception)
        self.triggerEvent("readystatechange")

    def _do_send(self):
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
            else:
                self.response = self.responseText

            self.triggerEvent("load", ProgressEvent())
        except requests.exceptions.Timeout:
            self.triggerEvent("timeout", ProgressEvent())
            self.readyState = self.DONE
        except requests.exceptions.RequestException:
            self.readyState = self.DONE
        finally:
            self.triggerEvent("loadend", ProgressEvent())
            self.triggerEvent("readystatechange")

    def send(self, data=None):
        if data is not None:
            self.__request.data = str(data)
        self.__thread = self.__group.spawn(self._do_send)
        if not self.__async:
            self.__thread.join()

    def getResponseHeader(self, header):
        pass

    def getAllResponseHeaders(self):
        pass

    def abort(self):
        pass


def xhr_factory(group):
    session = requests.Session()
    return lambda: XMLHttpRequest(group, session)
