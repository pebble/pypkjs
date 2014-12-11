#!/usr/bin/env python
from gevent import monkey
monkey.patch_all()

import zipfile
import json
import sys

import javascript.runtime
from runner.terminal import TerminalRunner
# from runner.websocket import WebsocketRunner



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
    runner = TerminalRunner(sys.argv[1], sys.argv[2:])
    # runner = WebsocketRunner(sys.argv[1], sys.argv[2:], 12346, '55189eacccc2c4c0252cd5f8037030c02a195174d7e0f78df598343258a098a7')
    runner.run()
