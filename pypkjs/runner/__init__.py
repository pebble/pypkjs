from __future__ import absolute_import
__author__ = 'katharine'

from gevent import monkey
monkey.patch_all()

import collections
import zipfile
from uuid import UUID
import gevent
import json
import logging
import os
import os.path
import shutil
import urlparse
import urllib

from libpebble2.services.appmessage import AppMessageService
import pypkjs.javascript as javascript
import pypkjs.javascript.runtime
from .pebble_manager import PebbleManager
from pypkjs.timeline import PebbleTimeline
from pypkjs.timeline.urls import URLManager


class Runner(object):
    PBW = collections.namedtuple('PBW', ('uuid', 'src', 'manifest', 'layouts'))

    def __init__(self, qemu, pbws, persist_dir=None, oauth_token=None, layout_file=None, block_private_addresses=False):
        self.qemu = qemu
        self.pebble = PebbleManager(qemu)
        self.persist_dir = persist_dir
        self.oauth_token = oauth_token
        self.pebble.handle_start = self.handle_start
        self.pebble.handle_stop = self.handle_stop
        # PBL-26034: Due to PBL-24009 we must be sure to respond to appmessages received with no JS running.
        # However, libpebble2 presently provides no way of NACKing. Making sure this exists is sufficient for
        # ACKs, so we just create it and pass it off. We should add NACKs later, though.
        self.appmessage = AppMessageService(self.pebble.pebble)
        self.pbws = {}
        self.logger = logging.getLogger("pypkjs")
        self.running_uuid = None
        self.js = None
        self.urls = URLManager()
        self.timeline = PebbleTimeline(self, persist=persist_dir, oauth=oauth_token, layout_file=layout_file)
        self.block_private_addresses = block_private_addresses
        self.load_cached_pbws()
        self.load_pbws(pbws)

    def load_pbws(self, pbws, start=False, cache=False):
        for pbw_path in pbws:
            with zipfile.ZipFile(pbw_path) as z:
                appinfo = z.open('appinfo.json').read()
                try:
                    z.getinfo('pebble-js-app.js')
                except KeyError:
                    src = None
                else:
                    src = z.open('pebble-js-app.js').read().decode('utf-8')
                layouts = {}
                platforms = [os.path.dirname(path) for path in z.namelist() if 'layouts.json' in path]
                for platform in platforms:
                    try:
                        layouts[platform] = json.load(z.open('%s/layouts.json' % platform))
                    except (KeyError, ValueError):
                        layouts[platform] = {}
            manifest = json.loads(appinfo)
            uuid = UUID(manifest['uuid'])
            if cache and self._pbw_cache_dir is not None:
                shutil.copy(pbw_path, os.path.join(self._pbw_cache_dir, '%s.pbw' % uuid))
            self.pbws[uuid] = self.PBW(uuid, src, manifest, layouts)
            if start:
                self.start_js(self.pbws[uuid])
        self.logger.info("Ready. Loaded apps: %s", ', '.join(map(str, self.pbws.keys())))

    def load_cached_pbws(self):
        cache_dir = self._pbw_cache_dir
        if cache_dir is not None:
            self.load_pbws([os.path.join(cache_dir, x) for x in os.listdir(cache_dir)])

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
        if pbw.src is None:
            return
        self.running_uuid = pbw.uuid
        self.js = javascript.runtime.JSRuntime(self.pebble, pbw.manifest, self, persist_dir=self.persist_dir,
                                               block_private_addresses=self.block_private_addresses)
        self.js.log_output = lambda m: self.log_output(m)
        self.js.open_config_page = lambda url, callback: self.open_config_page(url, callback)
        gevent.spawn(self.js.run, pbw.src)

    def timeline_mapping_for_app(self, app_uuid):
        try:
            pbw = self.pbws[app_uuid]
        except KeyError:
            return None
        return pbw.layouts.get(self.pebble.pebble.watch_platform, {})

    def stop_js(self):
        if self.js is not None:
            self.js.stop()
            self.js = None
            self.running_uuid = None

    def run(self):
        self.logger.info('Connecting to pebble')
        greenlet = self.pebble.connect()
        if self.pebble.timeline_is_supported:
            self.timeline.continuous_sync()
            self.timeline.do_maintenance()
        greenlet.join()

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

    @property
    def _pbw_cache_dir(self):
        if self.persist_dir is None:
            return None
        path = os.path.join(self.persist_dir, 'app_cache')
        if not os.path.exists(path):
            os.makedirs(path)
        return path
