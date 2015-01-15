__author__ = 'katharine'

import struct
import tempfile
import gevent
import ssl
from gevent import pywsgi
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler

from runner import Runner


def must_auth(f):
    def g(self, *args, **kwargs):
        if self.authed or not self.requires_auth:
            f(self, *args, **kwargs)
    return g

class WebsocketRunner(Runner):
    def __init__(self, qemu, pbws, port, token=None, ssl_root=None):
        self.port = port
        self.token = token
        self.requires_auth = (token is not None)
        self.authed = not self.requires_auth
        self.server = None
        self.ws = None
        self.ssl_root = ssl_root
        self.config_callback = None
        super(WebsocketRunner, self).__init__(qemu, pbws)

    def run(self):
        self.pebble.connect()
        self.patch_pebble()
        if self.ssl_root is not None:
            ssl_args = {
                'keyfile': '%s/server-key.pem' % self.ssl_root,
                'certfile': '%s/server-cert.pem' % self.ssl_root,
                'ca_certs': '%s/ca-cert.pem' % self.ssl_root,
                'ssl_version': ssl.PROTOCOL_TLSv1,
            }
        else:
            ssl_args = {}
        self.server = pywsgi.WSGIServer(("", self.port), self.handle_ws, handler_class=WebSocketHandler, **ssl_args)
        self.server.serve_forever()
        self.pebble.disconnect()

    def log_output(self, message):
        try:
            if self.ws is not None:
                self.ws.send(bytearray('\x02' + message))
        except WebSocketError:
            pass

    def open_config_page(self, url, callback):
        if self.ws:
            try:
                self.ws.send(bytearray(struct.pack('>BBI%ds' % len(url), 0x0a, 0x01, len(url), url)))
            except WebSocketError:
                pass
            else:
                self.config_callback = callback

    # evil monkeypatch
    def patch_pebble(self):
        real_write = self.pebble.pebble._ser.write
        def echoing_write(message):
            real_write(message)
            if self.ws is not None:
                try:
                    self.ws.send(bytearray('\x01' + message))
                except WebSocketError:
                    pass
        self.pebble.pebble._ser.write = echoing_write

        real_read = self.pebble.pebble._recv_message
        def echoing_read():
            source, endpoint, resp = real_read()
            if resp is not None:
                real_message = struct.pack('>HH', len(resp), endpoint) + resp
                if self.ws is not None and (self.authed or not self.requires_auth):
                    try:
                        self.ws.send(bytearray('\x00' + real_message))
                    except WebSocketError:
                        pass
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
        self.authed = not self.requires_auth

    def on_close(self):
        pass

    # https://pebbletechnology.atlassian.net/wiki/pages/viewpage.action?pageId=491742
    def on_message(self, message):
        if not isinstance(message, bytearray):
            print "not a bytearray"
            print message
            return
        opcode = message[0]
        opcode_handlers = {
            0x01: self.do_relay,
            0x04: self.do_install,
            0x06: self.do_phone_info,
            0x09: self.do_auth,
            0x0a: self.do_config_ws,
            0x0b: self.do_qemu_command,
        }

        if opcode in opcode_handlers:
            opcode_handlers[opcode](message[1:])

    @must_auth
    def do_phone_info(self, message):
        try:
            self.ws.send(bytearray("\x06pypkjs,0.0.0,qemu"))
        except WebSocketError:
            pass

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

    @must_auth
    def do_relay(self, message):
        self.pebble.pebble._ser.write(str(message))

    @must_auth
    def do_install(self, message):
        def go_do_install():
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(message)
                f.flush()
                try:
                    self.load_pbws([f.name])
                    self.pebble.pebble.install_app_pebble_protocol(f.name)

                except:
                    try:
                        self.ws.send(bytearray([0x05, 0x00, 0x00, 0x00, 0x01]))
                    except WebSocketError:
                        pass
                    raise
                else:
                    try:
                        self.ws.send(bytearray([0x05, 0x00, 0x00, 0x00, 0x00]))
                    except WebSocketError:
                        pass
        gevent.spawn(go_do_install)

    @must_auth
    def do_config_ws(self, message):
        if message[0] == 0x01:
            self.do_config()
            return
        if self.config_callback is None:
            return
        if message[0] == 0x02:
            length, = struct.unpack_from(">I", message, 1)
            result, = struct.unpack_from(">%ds" % length, message, 5)
            self.config_callback(result)
            self.config_callback = None
        elif message[0] == 0x03:
            self.config_callback("")
            self.config_callback = None
        else:
            print "what?"

    @must_auth
    def do_qemu_command(self, message):
        protocol = message[0]
        self.pebble.pebble._ser.write(str(message[1:]), protocol=protocol)
