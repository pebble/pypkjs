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
    def g(self, ws, *args, **kwargs):
        if not self.requires_auth or ws.authed:
            f(self, ws, *args, **kwargs)
    return g


class Websocket(object):
    def __init__(self, ws):
        self.ws = ws
        self.authed = False

    def send(self, message):
        self.ws.send(message)

    def receive(self):
        return self.ws.receive()

    def close(self):
        self.ws.close()


class WebsocketRunner(Runner):
    def __init__(self, qemu, pbws, port, token=None, ssl_root=None):
        self.port = port
        self.token = token
        self.requires_auth = (token is not None)
        self.authed = not self.requires_auth
        self.server = None
        self.websockets = []
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
        self.broadcast(bytearray('\x02' + message))

    def open_config_page(self, url, callback):
        self.broadcast(bytearray(struct.pack('>BBI%ds' % len(url), 0x0a, 0x01, len(url), url)))
        self.config_callback = callback

    # evil monkeypatch
    def patch_pebble(self):
        real_write = self.pebble.pebble._ser.write
        def echoing_write(message, **kwargs):
            real_write(message, **kwargs)
            if 'protocol' not in kwargs:
                self.broadcast(bytearray('\x01' + message))
        self.pebble.pebble._ser.write = echoing_write

        real_read = self.pebble.pebble._ser.read
        def echoing_read():
            source, protocol, data, data_again = real_read()
            if source == 'watch':
                self.broadcast(bytearray('\x00' + data))
            return source, protocol, data, data_again
        self.pebble.pebble._ser.read = echoing_read

    def handle_ws(self, environ, start_response):
        if environ['PATH_INFO'] == '/':
            ws = Websocket(environ['wsgi.websocket'])
            self.websockets.append(ws)
            self.on_open(ws)
            while True:
                try:
                    self.on_message(ws, ws.receive())
                except WebSocketError:
                    break
            self.on_close(ws)

    def on_open(self, ws, *args, **kwargs):
        ws.authed = not self.requires_auth

    def on_close(self, ws):
        self.websockets.remove(ws)

    def broadcast(self, message):
        to_remove = []
        for i, ws in enumerate(self.websockets):
            if ws.authed:
                try:
                    ws.send(message)
                except (WebSocketError, ssl.SSLError):
                    to_remove.append(i)
        for i in reversed(to_remove):
            del self.websockets[i]

    # https://pebbletechnology.atlassian.net/wiki/pages/viewpage.action?pageId=491742
    def on_message(self, ws, message):
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
            opcode_handlers[opcode](ws, message[1:])

    @must_auth
    def do_phone_info(self, ws, message):
        try:
            ws.send(bytearray("\x06pypkjs,0.0.0,qemu"))
        except WebSocketError:
            pass

    def do_auth(self, ws, message):
        length = message[0]
        token, = struct.unpack_from('<%ds' % length, message, 1)
        if token == self.token:
            ws.authed = True
            ws.send(bytearray([0x09, 0x00]))  # token okay
            ws.send(bytearray([0x08, 0xff]))  # send "connected" response immediately; we're always connected.
        else:
            ws.send(bytearray([0x09, 0x01]))  # bad token

    @must_auth
    def do_relay(self, ws, message):
        self.pebble.pebble._ser.write(str(message))

    @must_auth
    def do_install(self, ws, message):
        def go_do_install():
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(message)
                f.flush()
                try:
                    self.load_pbws([f.name])
                    self.pebble.pebble.install_app_pebble_protocol(f.name)

                except:
                    try:
                        ws.send(bytearray([0x05, 0x00, 0x00, 0x00, 0x01]))
                    except WebSocketError:
                        pass
                    raise
                else:
                    try:
                        ws.send(bytearray([0x05, 0x00, 0x00, 0x00, 0x00]))
                    except WebSocketError:
                        pass
        gevent.spawn(go_do_install)

    @must_auth
    def do_config_ws(self, ws, message):
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
    def do_qemu_command(self, ws, message):
        protocol = message[0]
        self.pebble.pebble._ser.write(str(message[1:]), protocol=protocol)
