__author__ = 'katharine'

import PyV8 as v8
import gevent
import gevent.pool
import gevent.queue
import gevent.hub

from javascript import PebbleKitJS
from javascript.exceptions import JSRuntimeException

make_proxy_extension = v8.JSExtension("runtime/internal/proxy", """
    function _make_proxies(proxy, origin, names) {
        names.forEach(function(name) {
            proxy[name] = eval("(function " + name + "() { return origin[name].apply(origin, arguments); })");
        });
        return proxy;
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
        return proxy;
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
            self.pjs.do_post_setup()

    def run(self, src, filename="pebble-js-app.js"):
        self.setup()

        with self.context:
            # go!
            print "JS starting"
            try:
                self.context.eval(src, filename)
            except (v8.JSError, JSRuntimeException) as e:
                self.log_output(e.stackTrace)
                self.log_output("JS failed.")
            except Exception as e:
                self.log_output(e.message)
                raise
            else:
                self.enqueue(self.pjs.pebble._connect)
                self.event_loop()
            self.pjs.shutdown()
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

    def is_configurable(self):
        return 'configurable' in self.manifest['capabilities']

    def do_config(self):
        self.enqueue(self.pjs.pebble._configure)

JSRuntime.runtimeCount = 0
