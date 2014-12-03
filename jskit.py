from gevent import monkey
monkey.patch_all()

import javascript.runtime


def run_script(src):
    js = javascript.runtime.JSRuntime('localhost:12344')
    js.run(src)

if __name__ == "__main__":
    run_script(open('pebble-js-app.js', 'r').read().decode('utf-8'))
