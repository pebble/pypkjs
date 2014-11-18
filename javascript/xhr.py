__author__ = 'katharine'

import PyV8 as v8


class XMLHttpRequest(v8.JSClass):
    UNSENT = 0
    OPENED = 1
    HEADERS_RECEIVED = 2
    LOADING = 3
    DONE = 4

    def __init__(self):
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

    def open(self, method, url, async=True, user=None, password=None):
        pass

    def overrideMimeType(self, mimetype):
        pass

    def send(self, data=None):
        pass

    def getResponseHeader(self, header):
        pass

    def getAllResponseHeaders(self):
        pass

    def abort(self):
        pass
