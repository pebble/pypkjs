from __future__ import absolute_import
__author__ = 'katharine'

import signal
import webbrowser
import BaseHTTPServer
import socket

from . import Runner


class TerminalRunner(Runner):
    def __init__(self, *args, **kwargs):
        self.port = None
        super(TerminalRunner, self).__init__(*args, **kwargs)
        signal.signal(signal.SIGUSR1, self.handle_sigusr)

    def log_output(self, message):
        print message.encode('utf-8')

    def open_config_page(self, url, callback):
        port = self._find_port()
        url = self.url_append_params(url, {'return_to': 'http://localhost:%d/close?' % port})
        webbrowser.open_new(url)
        self.serve_page(port, callback)

    def handle_sigusr(self, signum, frame):
        self.port = self._find_port()
        self.do_config()

    def serve_page(self, port, callback):
        running = [True]

        class TerminalConfigHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                path, query = self.path.split('?')
                if path == '/close':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write("ok")
                    running[0] = False
                    callback(query)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write("not found")

        server = BaseHTTPServer.HTTPServer(('', port), TerminalConfigHandler)
        while running[0]:
            server.handle_request()

    @staticmethod
    def _find_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        addr, port = s.getsockname()
        s.close()
        return port


