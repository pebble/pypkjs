__author__ = 'katharine'

import gevent
import PyV8 as v8

class Timers(object):
    def __init__(self, runtime):
        self._runtime = runtime
        self._timers = {}
        self._counter = 1
        self.extension = v8.JSExtension(self._runtime.ext_name('timers'), """
        (function() {
            native function _timers();
            _make_proxies(this, _timers(), ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval']);
        })();
        """, lambda f: lambda: self, dependencies=["runtime/internal/proxy"])

    def _exec_timer(self, timer_key, timeout_s, repeat, fn):
        while True:
            gevent.sleep(timeout_s)
            if timer_key in self._timers:
                if callable(fn):
                    self._runtime.enqueue(fn)
                else:
                    self._runtime.enqueue(self._runtime.context.eval, fn)
                if not repeat:
                    del self._timers[timer_key]
                    break

    def _run_timer(self, fn, timeout_ms, repeat):
        if timeout_ms < 4:
            timeout_ms = 4

        timer_id = self._counter
        timer_key = (timer_id, repeat)
        self._counter += 1

        timeout_s = timeout_ms / 1000.0
        timer = self._runtime.group.spawn(self._exec_timer, timer_key, timeout_s, repeat, fn)

        self._timers[timer_key] = timer
        timer.start()

        return timer_id

    def _clear_timer(self, timer_id, repeat):
        timer_key = (timer_id, repeat)
        if timer_key in self._timers:
            self._timers[timer_key].kill()
            del self._timers[timer_key]

    def setTimeout(self, fn, timeout):
        return self._run_timer(fn, timeout, False)

    def clearTimeout(self, timer_id):
        self._clear_timer(timer_id, False)

    def setInterval(self, fn, timeout):
        return self._run_timer(fn, timeout, True)

    def clearInterval(self, timer_id):
        return self._clear_timer(timer_id, True)
