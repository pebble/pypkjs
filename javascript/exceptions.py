__author__ = 'katharine'

import PyV8 as v8


class JSRuntimeException(Exception):
    def __init__(self, runtime, message):
        # This is an ugly hack to generate a stack trace in JavaScript.
        try:
            runtime.context.eval('throw new Error("");')
        except v8.JSError as e:
            lines = e.stackTrace.split('\n')
            del lines[1]
            lines[0] = "Error: %s" % message
            Exception.__init__(self, message)
            self.stackTrace = '\n'.join(lines)
