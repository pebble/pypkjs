#!/usr/bin/env python
from gevent import monkey
monkey.patch_all()

import zipfile
import json
import sys

import javascript.runtime
from runner.terminal import TerminalRunner


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
    runner = TerminalRunner(sys.argv[1], sys.argv[2:], "data")
    runner.run()

