__author__ = 'katharine'

from runner import Runner


class TerminalRunner(Runner):
    def log_output(self, message):
        print message
