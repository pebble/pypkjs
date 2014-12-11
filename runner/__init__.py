__author__ = 'katharine'

import collections
import zipfile
from uuid import UUID
import gevent
import json

import javascript
from pebble_manager import PebbleManager


class Runner(object):
    PBW = collections.namedtuple('PBW', ('uuid', 'src', 'manifest'))

    def __init__(self, qemu, pbws):
        self.qemu = qemu
        self.pebble = PebbleManager(qemu)
        self.pebble.handle_start = self.handle_start
        self.pebble.handle_stop = self.handle_stop
        self.pbws = {}
        self.running_uuid = None
        self.js = None
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
        print "ready with apps %s" % ', '.join(map(str, self.pbws.keys()))

    def handle_start(self, uuid):
        print uuid
        if uuid in self.pbws:
            print "starting js for %s" % uuid
            self.start_js(self.pbws[uuid])

    def handle_stop(self, uuid):
        if uuid == self.running_uuid:
            print "stopping js"
            self.stop_js()

    def start_js(self, pbw):
        self.stop_js()
        self.running_uuid = pbw.uuid
        self.js = javascript.runtime.JSRuntime(self.pebble, pbw.manifest)
        self.js.log_output = lambda m: self.log_output(m)
        gevent.spawn(self.js.run, pbw.src)


    def stop_js(self):
        if self.js is not None:
            self.js.stop()
            self.js = None
            self.running_uuid = None

    def run(self):
        print 'connecting'
        self.pebble.connect()
        while self.pebble.pebble._alive:
            gevent.sleep(0.5)

    def log_output(self, message):
        raise NotImplemented