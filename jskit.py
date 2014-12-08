from gevent import monkey
monkey.patch_all()

import zipfile
import json
import gevent
from uuid import UUID

import javascript.runtime
from pebble_manager import PebbleManager


class Runner(object):
    def __init__(self, qemu, pbw):
        self.qemu = qemu
        self.pebble = PebbleManager(qemu)
        self.pebble.handle_start = self.handle_start
        self.pebble.handle_stop = self.handle_stop
        self.js = None
        self.manifest = None
        self.uuid = None
        self.src = None
        self.load_pbw(pbw)

    def load_pbw(self, pbw_path):
        with zipfile.ZipFile(pbw_path) as z:
            appinfo = z.open('appinfo.json').read()
            self.src = z.open('pebble-js-app.js').read().decode('utf-8')
        self.manifest = json.loads(appinfo)
        self.uuid = UUID(self.manifest['uuid'])
        print "ready with app %s" % self.uuid

    def handle_start(self, uuid):
        if uuid == self.uuid:
            print "starting js"
            self.start_js()

    def handle_stop(self, uuid):
        if uuid == self.uuid:
            print "stopping js"
            self.stop_js()

    def start_js(self):
        self.stop_js()
        self.js = javascript.runtime.JSRuntime(self.pebble, self.manifest)
        gevent.spawn(self.js.run, self.src)


    def stop_js(self):
        if self.js is not None:
            self.js.stop()
            self.js = None

    def run(self):
        print 'connecting'
        self.pebble.connect()
        while self.pebble.pebble._alive:
            gevent.sleep(0.5)


def run_script(qemu, src):
    js = javascript.runtime.JSRuntime(qemu, {'appKeys': {}, 'capabilities': ['location'], 'uuid': '00000000-0000-0000-0000-000000000001'})
    js.run(src)


def run_pbw(qemu, pbw_path):
    with zipfile.ZipFile(pbw_path) as z:
        appinfo = z.open('appinfo.json').read()
        src = z.open('pebble-js-app.js').read().decode('utf-8')
    manifest = json.loads(appinfo)
    js = javascript.runtime.JSRuntime(qemu, manifest)
    js.run(src)

if __name__ == "__main__":
    # run_script('localhost:12344', open('pebble-js-app.js', 'r').read().decode('utf-8'))
    runner = Runner('localhost:12344', '/Users/katharine/Downloads/twc (5).pbw')
    runner.run()
