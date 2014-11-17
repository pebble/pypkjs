__author__ = 'katharine'

import PyV8 as v8


class Console(v8.JSClass):
    def log(self, *params):
        print ' '.join([str(x) for x in params])

    def warn(self, *params):
        self.log(params)

    def info(self, *params):
        self.log(params)

    def error(self, *params):
        self.log(params)