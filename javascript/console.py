__author__ = 'katharine'

import PyV8 as v8


class Console(object):
    def __init__(self, runtime):
        self.runtime = runtime
        self.extension = v8.JSExtension(self.runtime.ext_name("console"), """
        console = new (function () {
            native function _internal_console();
            _make_proxies(this, _internal_console(), ['log', 'warn', 'info', 'error']);
        })();
        """, lambda f: lambda: self, dependencies=["runtime/internal/proxy"])

    def log(self, *params):
        self.runtime.log_output(' '.join([x.toString() if hasattr(x, 'toString') else str(x) for x in params]))

    def warn(self, *params):
        self.log(*params)

    def info(self, *params):
        self.log(*params)

    def error(self, *params):
        self.log(*params)