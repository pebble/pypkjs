__author__ = 'katharine'

import PyV8 as v8
import gevent
import gevent.pool
import gevent.queue
import gevent.hub

from javascript import PebbleKitJS
from javascript.exceptions import JSRuntimeException


class JSRuntime(object):
    def __init__(self, qemu, manifest):
        self.group = gevent.pool.Group()
        self.queue = gevent.queue.Queue()
        self.qemu = qemu
        self.manifest = manifest

    def setup(self):
        self.pjs = PebbleKitJS(self, self.qemu)
        self.context = v8.JSContext(self.pjs)
        with self.context:
            # Do some setup
            self.context.eval("this.toString = function() { return '[object Window]'; }")
            self.context.eval("window = this;")

    def run(self, src, filename="pebble-js-app.js"):
        self.setup()

        with self.context:
            self.pjs._set_typedarrays(self)
            # go!
            print "JS starting"
            try:
                self.context.eval(src, filename)
            except SyntaxError as e:
                self.log_output(e.message)
                self.log_output("JS failed.")
            except Exception as e:
                self.log_output(JSRuntimeException(self, e.message).stackTrace)
                raise
            self.group.spawn(self.pjs.Pebble._connect)

            self.event_loop()
            self.group.kill(timeout=2)
            print "JS finished"

    def stop(self):
        self.queue.put(StopIteration)

    def enqueue(self, fn, *args, **kwargs):
        self.queue.put((fn, args, kwargs))

    def event_loop(self):
        try:
            for fn, args, kwargs in self.queue:
                fn(*args, **kwargs)
        except gevent.hub.LoopExit:
            print "Runtime ran out of events; terminating."

    def log_output(self, message):
        raise NotImplemented
