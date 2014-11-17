import PyV8 as v8
import pyev

from javascript import PebbleKitJS


def run_script(src):
    loop = pyev.Loop()
    context = v8.JSContext(PebbleKitJS(loop))
    with context:
        # Do some setup
        context.eval("this.toString = function() { return '[object Window]'; }")
        context.eval("window = this;")

    with context:
        # go!
        context.eval(src)
        loop.start()
