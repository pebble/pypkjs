#!/usr/bin/env python
from gevent import monkey
monkey.patch_all()

import sys

from runner.websocket import WebsocketRunner

if __name__ == "__main__":
    runner = WebsocketRunner(sys.argv[1], sys.argv[4:], int(sys.argv[2]), sys.argv[3])
    runner.run()
