__author__ = 'katharine'

import PyV8 as v8
from geolocation import Geolocation
from javascript.exceptions import JSRuntimeException


class Navigator(v8.JSClass):
    def __init__(self, runtime):
        self._runtime = runtime
        # W3C spec says that if geolocation is disabled, navigator.geolocation should not exist.
        if 'location' in runtime.manifest.get('capabilities', []):
            self.geolocation = Geolocation(runtime)

        self.language = "en-GB"

    def __getattr__(self, item):
        # __getattr__ is only called if something does not exist. Therefore, if it's called, geolocation
        # does not exist.
        # This approach lets us report it doesn't exist if tested for (e.g. `'geolocation' in navigator`),
        # but throw an informative exception if it's accessed.
        if item == 'geolocation':
            raise JSRuntimeException(
                self._runtime,
                "You must add 'location' to the appinfo.json capabilities array to access geolocation."
            )
        else:
            raise AttributeError

