from __future__ import absolute_import
__author__ = 'katharine'

import pypkjs.PyV8 as v8
import time


class Performance(object):
    # This is an approximation for now
    def __init__(self, runtime):
        self.extension = v8.JSExtension(runtime.ext_name("performance"), """
            performance = new (function() {
                native function _time();
                var start = _time();

                this.now = function() {
                    return (_time() - start) * 1000;
                };
            })();
        """, lambda f: lambda: time.time())
