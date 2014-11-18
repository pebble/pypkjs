__author__ = 'katharine'

import PyV8 as v8
from console import Console
from performance import Performance
from timers import Timers
from localstorage import LocalStorage
from jsJSON import JSON
from pebble import Pebble
from xhr import XMLHttpRequest


class PebbleKitJS(v8.JSClass):
    def __init__(self, loop):
        self.console = Console()
        self.performance = Performance()
        self.localStorage = LocalStorage()
        self.JSON = JSON()
        self.Pebble = Pebble()
        self.XMLHttpRequest = XMLHttpRequest

        timerImpl = Timers(loop)
        self.setTimeout = lambda x, y: timerImpl.setTimeout(x, y)
        self.clearTimeout = lambda x: timerImpl.clearTimeout(x)
        self.setInterval = lambda x, y: timerImpl.setInterval(x, y)
        self.clearInterval = lambda x: timerImpl.clearInterval(x)
