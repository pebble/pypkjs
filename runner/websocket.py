__author__ = 'katharine'

import struct
import tempfile
import gevent
from gevent import pywsgi
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler

from runner import Runner


class WebsocketRunner(Runner):
    def __init__(self, qemu, pbws, port, token):
        self.port = port
        self.token = token
        self.authed = False
        self.server = None
        self.ws = None
        super(WebsocketRunner, self).__init__(qemu, pbws)

    def run(self):
        self.pebble.connect()
        self.patch_pebble()
        self.server = pywsgi.WSGIServer(("", self.port), self.handle_ws, handler_class=WebSocketHandler)
        self.server.serve_forever()
        self.pebble.disconnect()

    def log_output(self, message):
        if self.ws is not None:
            self.ws.send(bytearray('\x02' + message))

    # evil monkeypatch
    def patch_pebble(self):
        real_write = self.pebble.pebble._ser.write
        def echoing_write(message):
            real_write(message)
            if self.ws is not None:
                self.ws.send(bytearray('\x01' + message))
        self.pebble.pebble._ser.write = echoing_write

        real_read = self.pebble.pebble._recv_message
        def echoing_read():
            source, endpoint, resp = real_read()
            if resp is not None:
                real_message = struct.pack('>HH', len(resp), endpoint) + resp
                if self.ws is not None:
                    self.ws.send(bytearray('\x00' + real_message))
            return source, endpoint, resp
        self.pebble.pebble._recv_message = echoing_read

    def handle_ws(self, environ, start_response):
        if environ['PATH_INFO'] == '/':
            self.ws = environ['wsgi.websocket']
            self.on_open()
            while True:
                try:
                    self.on_message(self.ws.receive())
                except WebSocketError:
                    break
            self.on_close()

    def on_open(self, *args, **kwargs):
        self.authed = False

    def on_close(self):
        self.server.stop()

    # https://pebbletechnology.atlassian.net/wiki/pages/viewpage.action?pageId=491742
    def on_message(self, message):
        if not isinstance(message, bytearray):
            print "not a bytearray"
            return
        opcode = message[0]
        opcode_handlers = {
            0x01: self.do_relay,
            0x04: self.do_install,
            0x09: self.do_auth,
        }

        if opcode in opcode_handlers:
            opcode_handlers[opcode](message[1:])

    def do_auth(self, message):
        length = message[0]
        token, = struct.unpack_from('<%ds' % length, message, 1)
        print token, self.token
        if token == self.token:
            self.authed = True
            self.ws.send(bytearray([0x09, 0x00]))  # token okay
            self.ws.send(bytearray([0x08, 0xff]))  # send "connected" response immediately; we're always connected.
        else:
            self.ws.send(bytearray([0x09, 0x01]))  # bad token

    def do_relay(self, message):
        self.pebble.pebble._ser.write(str(message))

    def do_install(self, message):
        def go_do_install():
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(message)
                f.flush()
                try:
                    self.pebble.pebble.install_app_pebble_protocol(f.name)
                    self.pebble.register_endpoints()
                    # Install it for us, too.
                    self.load_pbws([f.name], start=True)

                except:
                    self.ws.send(bytearray([0x05, 0x01]))
                    raise
                else:
                    self.ws.send(bytearray([0x05, 0x00]))
        gevent.spawn(go_do_install)
