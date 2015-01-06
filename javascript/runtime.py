__author__ = 'katharine'

import PyV8 as v8
import gevent
import gevent.pool
import gevent.queue
import gevent.hub

from javascript import PebbleKitJS
from javascript.exceptions import JSRuntimeException
from javascript.console import Console
from javascript.performance import Performance
from javascript.localstorage import LocalStorage
from javascript.pebble import Pebble
from javascript.xhr import prepare_xhr
from javascript.navigator import Navigator

make_proxy_extension = v8.JSExtension("runtime/internal/proxy", """
    function _make_proxies(proxy, origin, names) {
        names.forEach(function(name) {
            proxy[name] = function() { origin[name].apply(origin, arguments); };
        });
    }
    function _make_properties(proxy, origin, names) {
        names.forEach(function(name) {
            Object.defineProperty(proxy, name, {
                configurable: false,
                enumerable: true,
                get: function() {
                    return origin[name];
                },
                set: function(value) {
                    origin[name] = value;
                }
            });
        });
    }
""")


class JSRuntime(object):
    def __init__(self, qemu, manifest):
        self.group = gevent.pool.Group()
        self.queue = gevent.queue.Queue()
        self.qemu = qemu
        self.manifest = manifest
        self.runtime_id = JSRuntime.runtimeCount
        JSRuntime.runtimeCount += 1

    def setup(self):
        self.pjs = PebbleKitJS(self, self.qemu)
        self.context = v8.JSContext(extensions=self.pjs.get_extension_names())
        with self.context:
            # Do some setup
            self.context.eval("this.toString = function() { return '[object Window]'; }")
            self.context.eval("window = this;")
            prepare_xhr(self)

    def run(self, src, filename="pebble-js-app.js"):
        self.setup()

        with self.context:
            # go!
            print "JS starting"
            try:
                self.context.eval(src, filename)
            except SyntaxError as e:
                # print v8.JSStackTrace.GetCurrentStackTrace(10, v8.JSStackTrace.Options.Detailed)
                self.log_output(e.message)
                self.log_output("JS failed.")
            except Exception as e:
                self.log_output(JSRuntimeException(self, e.message).stackTrace)
                raise
            self.group.spawn(self.pjs.pebble._connect)

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

    def ext_name(self, name):
        return "instance/%d/runtime/%s" % (self.runtime_id, name)
JSRuntime.runtimeCount = 0