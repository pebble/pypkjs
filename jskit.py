from gevent import monkey; monkey.patch_all()
import PyV8 as v8
import gevent
import gevent.pool

import javascript.runtime


def run_script(src):
    js = javascript.runtime.JSRuntime()
    js.run(src)

if __name__ == "__main__":
    run_script(open('pebble-js-app.js', 'r').read().decode('utf-8'))
