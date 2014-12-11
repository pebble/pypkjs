__author__ = 'katharine'

import PyV8 as v8
from console import Console
from performance import Performance
from timers import Timers
from localstorage import LocalStorage
from pebble import Pebble
from xhr import xhr_factory
from navigator import Navigator


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
