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

        self.Uint8Array = typedarrays.Uint8Array
        self.Int8Array = typedarrays.Int8Array
        self.Uint16Array = typedarrays.Uint16Array
        self.Int16Array = typedarrays.Int16Array
        self.Uint32Array = typedarrays.Uint32Array
        self.Int32Array = typedarrays.Int32Array
