from __future__ import absolute_import
__author__ = 'katharine'

import gevent
import pypkjs.PyV8 as v8

class Timers(object):
    def __init__(self, runtime):
        self.runtime = runtime
        self.timers = {}
        self.counter = 1
        self.extension = v8.JSExtension(self.runtime.ext_name('timers'), """
        (function() {
            native function _timers();
            _make_proxies(this, _timers(), ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval']);
        })();
        """, lambda f: lambda: self, dependencies=["runtime/internal/proxy"])

    def _exec_timer(self, timer_key, timeout_s, repeat, fn):
        while True:
            gevent.sleep(timeout_s)
            if timer_key in self.timers:
                if callable(fn):
                    self.runtime.enqueue(fn)
                else:
                    self.runtime.enqueue(self.runtime.context.eval, fn)
                if not repeat:
                    del self.timers[timer_key]
                    break

    def _run_timer(self, fn, timeout_ms, repeat):
        if timeout_ms < 4:
            timeout_ms = 4

        timer_id = self.counter
        timer_key = (timer_id, repeat)
        self.counter += 1

        timeout_s = timeout_ms / 1000.0
        timer = self.runtime.group.spawn(self._exec_timer, timer_key, timeout_s, repeat, fn)

        self.timers[timer_key] = timer
        timer.start()

        return timer_id

    def _clear_timer(self, timer_id, repeat):
        timer_key = (timer_id, repeat)
        if timer_key in self.timers:
            self.timers[timer_key].kill()
            del self.timers[timer_key]

    def setTimeout(self, fn, timeout):
        return self._run_timer(fn, timeout, False)

    def clearTimeout(self, timer_id):
        self._clear_timer(timer_id, False)

    def setInterval(self, fn, timeout):
        return self._run_timer(fn, timeout, True)

    def clearInterval(self, timer_id):
        return self._clear_timer(timer_id, True)
