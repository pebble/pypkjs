from __future__ import absolute_import
__author__ = 'katharine'

import pypkjs.PyV8 as v8


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
        # kOverview == kLineNumber | kColumnOffset | kScriptName | kFunctionName
        trace_str = str(v8.JSStackTrace.GetCurrentStackTrace(2, v8.JSStackTrace.Options.Overview))
        try:
            frames = v8.JSError.parse_stack(trace_str.strip())
            caller_frame = frames[0]
            filename = caller_frame[1]
            line_num = caller_frame[2]
            file_and_line = u"{}:{}".format(filename, line_num)
        except:
            file_and_line = u"???:?:?"
        log_str = u' '.join([x.toString().decode('utf-8') if hasattr(x, 'toString')
                                           else bytes(x).decode('utf-8') for x in params])
        self.runtime.log_output(u"{} {}".format(file_and_line, log_str))

    def warn(self, *params):
        self.log(*params)

    def info(self, *params):
        self.log(*params)

    def error(self, *params):
        self.log(*params)