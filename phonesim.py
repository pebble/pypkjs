#!/usr/bin/env python
from gevent import monkey
monkey.patch_all()

import logging
import sys
import argparse

from runner.websocket import WebsocketRunner

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Emulate a phone running the Pebble app')
    parser.add_argument('--qemu', default='127.0.0.1:12344', help="Location of qemu bluetooth socket")
    parser.add_argument('--port', default=9000, type=int, help="Port for phone websocket to listen on")
    parser.add_argument('--token', help="Token for the websocket to require as authentication")
    parser.add_argument('--ssl-root', help="Root for SSL certs, containing server-cert.pem and server-key.pem")
    parser.add_argument('--persist', help="Directory in which to read and write persistent data (localStorage, timeline)")
    parser.add_argument('--oauth', default=None, help="Pebble OAuth token.")
    parser.add_argument('--layout', default=None, help="Path to a firmware layout.json file on disk.")
    parser.add_argument('--debug', action='store_true', help="Very, very verbose debug spew.")
    parser.add_argument('pbws', nargs='*', help="Set of pbws.")
    args = parser.parse_args()
    print args
    logging.basicConfig()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    runner = WebsocketRunner(args.qemu,args.pbws, args.port, token=args.token, ssl_root=args.ssl_root,
                             persist_dir=args.persist, oauth_token=args.oauth, layout_file=args.layout)
    runner.run()
