from gevent import monkey; monkey.patch_all()
import PyV8 as v8
import gevent
import gevent.pool

from javascript import PebbleKitJS


def run_script(src):
    group = gevent.pool.Group()
    pjs = PebbleKitJS(group)
    context = v8.JSContext(pjs)
    with context:
        # Do some setup
        context.eval("this.toString = function() { return '[object Window]'; }")
        context.eval("window = this;")

    with context:
        # go!
        context.eval(src)
        group.add(gevent.spawn_later(0.2, pjs.Pebble._ready))
        group.join()

if __name__ == "__main__":
    run_script(open('pebble-js-app.js', 'r').read().decode('utf-8'))
