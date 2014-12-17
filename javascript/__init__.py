__author__ = 'katharine'

import PyV8 as v8
from console import Console
from performance import Performance
from timers import Timers
from localstorage import LocalStorage
from pebble import Pebble
from xhr import xhr_factory
from navigator import Navigator
import typedarrays

class PebbleKitJS(v8.JSClass):
    def __init__(self, runtime, pebble):
        self.console = Console(runtime)
        self.performance = Performance()
        self.localStorage = LocalStorage()
        self.Pebble = Pebble(runtime, pebble)
        self.XMLHttpRequest = xhr_factory(runtime)
        self.navigator = Navigator(runtime)

        timer_impl = Timers(runtime)
        self.setTimeout = timer_impl.setTimeout
        self.clearTimeout = timer_impl.clearTimeout
        self.setInterval = timer_impl.setInterval
        self.clearInterval = timer_impl.clearInterval

    def _set_typedarrays(self, runtime):
        with runtime.context:
            l = runtime.context.locals
            l.ArrayBuffer = typedarrays.ArrayBuffer
            l.Uint8Array = typedarrays.Uint8Array
            l.Int8Array = typedarrays.Int8Array
            l.Uint16Array = typedarrays.Uint16Array
            l.Int16Array = typedarrays.Int16Array
            l.Uint32Array = typedarrays.Uint32Array
            l.Int32Array = typedarrays.Int32Array
            # l.DataView = typedarrays.DataView
