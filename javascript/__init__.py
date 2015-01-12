__author__ = 'katharine'

import PyV8 as v8
from console import Console
from performance import Performance
from timers import Timers
from localstorage import LocalStorage
from pebble import Pebble
from xhr import prepare_xhr
from navigator import Navigator
import typedarrays

class PebbleKitJS(object):
    def __init__(self, runtime, pebble):
        self.runtime = runtime
        self.pebble = Pebble(runtime, pebble)

        self.extensions = [
            Console(runtime),
            Performance(runtime),
            LocalStorage(runtime),
            Navigator(runtime),
            Timers(runtime),
            self.pebble,
        ]

    def get_extension_names(self):
        return [x.extension.name for x in self.extensions] + ["runtime/events/progress", "runtime/xhr", "runtime/geolocation/position", "runtime/geolocation/coordinates"]

    def do_post_setup(self):
        prepare_xhr(self.runtime)

    def shutdown(self):
        self.pebble._shutdown()
