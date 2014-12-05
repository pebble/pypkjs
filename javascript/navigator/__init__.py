__author__ = 'katharine'

import PyV8 as v8
from geolocation import Geolocation


class Navigator(v8.JSClass):
    def __init__(self, runtime):
        # W3C spec says that if geolocation is disabled, navigator.geolocation should not exist.
        if 'location' in runtime.manifest.get('capabilities', []):
            self.geolocation = Geolocation(runtime)
