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
    def __init__(self, group):
        self.console = Console()
        self.performance = Performance()
        self.localStorage = LocalStorage()
        self.JSON = JSON()
        self.Pebble = Pebble()
        self.XMLHttpRequest = XMLHttpRequest

        timerImpl = Timers(group)
        self.setTimeout = timerImpl.setTimeout
        self.clearTimeout = timerImpl.clearTimeout
        self.setInterval = timerImpl.setInterval
        self.clearInterval = timerImpl.clearInterval
