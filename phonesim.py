#!/usr/bin/env python
from gevent import monkey
monkey.patch_all()

import sys
import argparse

from runner.websocket import WebsocketRunner

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Emulate a phone running the Pebble app')
    parser.add_argument('--qemu', default='127.0.0.1:12344', help="Location of qemu bluetooth socket")
    parser.add_argument('--port', default=9000, type=int, help="Port for phone websocket to listen on")
    parser.add_argument('--token', required=True, help="Token for the websocket to require as authentication")
    parser.add_argument('--ssl-root', help="Root for SSL certs, containing server-cert.pem and server-key.pem")
    parser.add_argument('pbws', nargs='*', help="Set of pbws.")
    args = parser.parse_args()
    print args
    runner = WebsocketRunner(args.qemu, args.pbws, args.port, args.token, ssl_root=args.ssl_root)
    runner.run()
