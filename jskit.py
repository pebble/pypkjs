import PyV8 as v8
import pyev

from javascript import PebbleKitJS


def run_script(src):
    loop = pyev.Loop()
    pjs = PebbleKitJS(loop)
    context = v8.JSContext(pjs)
    with context:
        # Do some setup
        context.eval("this.toString = function() { return '[object Window]'; }")
        context.eval("window = this;")

    with context:
        # go!
        context.eval(src)
        ready_timer = loop.timer(0.2, 0, lambda a, b: pjs.Pebble._ready())
        ready_timer.start()
        loop.start()

if __name__ == "__main__":
    run_script(open('pebble-js-app.js', 'r').read().decode('utf-8'))
