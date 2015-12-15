from __future__ import absolute_import
__author__ = 'katharine'

import pypkjs.PyV8 as v8
from .geolocation import Geolocation


class Navigator(object):
    def __init__(self, runtime):

        self._runtime = runtime
        self._runtime = runtime

        self.extension = v8.JSExtension(runtime.ext_name("navigator"), """
        navigator = new (function() {
            native function _internal_location();
            this.language = 'en-GB';

            var location = _internal_location();
            if(true) { // TODO: this should be a check on geolocation being enabled.
                this.geolocation = new (function() {
                    _make_proxies(this, location, ['getCurrentPosition', 'watchPosition', 'clearWatch']);
                })();
            }
        })();
        """, lambda f: lambda: Geolocation(runtime), dependencies=["runtime/internal/proxy"])

