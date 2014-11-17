__author__ = 'katharine'

import PyV8 as v8


class Timers(object):
    def __init__(self, loop):
        self._loop = loop
        self._timers = {}
        self._counter = 1

    def _exec_timer(self, w, events):
        timer_key, repeat, fn = w.data
        if not repeat:
            del self._timers[timer_key]
        fn()

    def _run_timer(self, fn, timeout, repeat):
        if timeout < 4:
            timeout = 4

        timer_id = self._counter
        timer_key = (timer_id, repeat)
        self._counter += 1

        timeout_ms = timeout / 1000.0
        timer = self._loop.timer(timeout_ms, timeout_ms if repeat else 0, self._exec_timer, (timer_key, repeat, fn))

        self._timers[timer_key] = timer
        timer.start()

        return timer_id

    def _clear_timer(self, timer_id, repeat):
        timer_key = (timer_id, repeat)
        if timer_key in self._timers:
            self._timers[timer_id].stop()
            del self._timers[timer_key]

    def setTimeout(self, fn, timeout):
        return self._run_timer(fn, timeout, False)

    def clearTimeout(self, timer_id):
        self._clear_timer(timer_id, False)

    def setInterval(self, fn, timeout):
        return self._run_timer(fn, timeout, True)

    def clearInterval(self, timer_id):
        return self._clear_timer(timer_id, True)
