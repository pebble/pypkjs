__author__ = 'katharine'
import PyV8 as v8
import time


class Performance(v8.JSClass):
    # This is an approximation for now
    def __init__(self):
        self.start = time.time()
        v8.JSClass.__init__(self)

    def now(self):
        return (time.time() - self.start) * 1000
