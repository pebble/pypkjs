__author__ = 'katharine'

import collections
import zipfile
from uuid import UUID
import gevent
import json
import logging
import urlparse
import urllib

import javascript
import javascript.runtime
from pebble_manager import PebbleManager
from timeline import PebbleTimeline
import timeline.urls


class Runner(object):
    PBW = collections.namedtuple('PBW', ('uuid', 'src', 'manifest'))

    def __init__(self, qemu, pbws, persist_dir=None, oauth_token=None, layout_file=None):
        self.qemu = qemu
        self.pebble = PebbleManager(qemu)
        self.persist_dir = persist_dir
        self.oauth_token = oauth_token
        self.pebble.handle_start = self.handle_start
        self.pebble.handle_stop = self.handle_stop
        self.pbws = {}
        self.logger = logging.getLogger("pypkjs")
        self.running_uuid = None
        self.js = None
        self.urls = timeline.urls.URLManager()
        self.timeline = PebbleTimeline(self, persist=persist_dir, oauth=oauth_token, layout_file=layout_file)
        self.load_pbws(pbws)

    def load_pbws(self, pbws, start=False):
        for pbw_path in pbws:
            with zipfile.ZipFile(pbw_path) as z:
                try:
                    z.getinfo('pebble-js-app.js')
                except KeyError:
                    continue
                appinfo = z.open('appinfo.json').read()
                src = z.open('pebble-js-app.js').read().decode('utf-8')
            manifest = json.loads(appinfo)
            uuid = UUID(manifest['uuid'])
            self.pbws[uuid] = self.PBW(uuid, src, manifest)
            if start:
                self.start_js(self.pbws[uuid])
        self.logger.info("Ready. Loaded apps: %s", ', '.join(map(str, self.pbws.keys())))

    def handle_start(self, uuid):
        self.logger.info("Starting %s", uuid)
        if uuid in self.pbws:
            self.logger.info("starting js for %s", uuid)
            self.start_js(self.pbws[uuid])

    def handle_stop(self, uuid):
        if uuid == self.running_uuid:
            self.logger.info("stopping js")
            self.stop_js()

    def start_js(self, pbw):
        self.stop_js()
        self.running_uuid = pbw.uuid
        self.js = javascript.runtime.JSRuntime(self.pebble, pbw.manifest, self)
        self.js.log_output = lambda m: self.log_output(m)
        self.js.open_config_page = lambda url, callback: self.open_config_page(url, callback)
        gevent.spawn(self.js.run, pbw.src)


    def stop_js(self):
        if self.js is not None:
            self.js.stop()
            self.js = None
            self.running_uuid = None

    def run(self):
        self.logger.info('Connecting to pebble')
        self.pebble.connect()
        self.timeline.continuous_sync()
        self.timeline.do_maintenance()
        while self.pebble.pebble._alive:
            gevent.sleep(0.5)

    @property
    def account_token(self):
        return "0123456789abcdef0123456789abcdef"

    @property
    def watch_token(self):
        return "0123456789abcdef0123456789abcdef"

    def do_config(self):
        if self.js is None:
            self.log_output("No JS found, can't show configuration.")
            return
        self.js.do_config()

    def log_output(self, message):
        raise NotImplemented

    def open_config_page(self, url, callback):
        raise NotImplemented

    @staticmethod
    def url_append_params(url, params):
        parsed = urlparse.urlparse(url, "http")
        query = parsed.query
        if parsed.query != '':
            query += '&'

        encoded_params = urllib.urlencode(params)
        query += encoded_params
        return urlparse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))
