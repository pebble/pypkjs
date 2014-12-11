__author__ = 'katharine'

import PyV8 as v8


class Console(v8.JSClass):
    def __init__(self, runtime):
        self._runtime = runtime
        super(Console, self).__init__()

    def log(self, *params):
        self._runtime.log_output(' '.join([x.toString() if hasattr(x, 'toString') else str(x) for x in params]))

    def warn(self, *params):
        self.log(params)

    def info(self, *params):
        self.log(params)

    def error(self, *params):
        self.log(params)