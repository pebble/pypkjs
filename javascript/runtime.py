__author__ = 'katharine'

import PyV8 as v8
import gevent
import gevent.pool
import gevent.queue
import gevent.hub
import logging

from javascript import PebbleKitJS
from javascript.exceptions import JSRuntimeException

logger = logging.getLogger('pypkjs.javascript.pebble')

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
    def __init__(self, qemu, manifest, runner, persist_dir=None):
        self.group = gevent.pool.Group()
        self.queue = gevent.queue.Queue()
        self.qemu = qemu
        self.manifest = manifest
        self.runner = runner
        self.runtime_id = JSRuntime.runtimeCount
        self.persist_dir = persist_dir
        JSRuntime.runtimeCount += 1

    def setup(self):
        self.pjs = PebbleKitJS(self, self.qemu, persist=self.persist_dir)
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
            logger.info("JS starting")
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
            finally:
                self.pjs.shutdown()
                self.group.kill(timeout=2)
                logger.info("JS finished")

    def stop(self):
        self.queue.put(StopIteration)

    def enqueue(self, fn, *args, **kwargs):
        self.queue.put((fn, args, kwargs))

    def event_loop(self):
        try:
            for fn, args, kwargs in self.queue:
                try:
                    fn(*args, **kwargs)
                except (v8.JSError, JSRuntimeException) as e:
                    self.log_output("Error running asynchronous JavaScript:")
                    self.log_output(e.stackTrace)
        except gevent.hub.LoopExit:
            logger.warning("Runtime ran out of events; terminating.")

    def log_output(self, message):
        raise NotImplemented

    def ext_name(self, name):
        return "instance/%d/runtime/%s" % (self.runtime_id, name)

    def is_configurable(self):
        return 'configurable' in self.manifest['capabilities']

    def do_config(self):
        self.enqueue(self.pjs.pebble._configure)

JSRuntime.runtimeCount = 0
