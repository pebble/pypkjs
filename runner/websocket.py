__author__ = 'katharine'

import gevent
from gevent import pywsgi
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
import json
import logging
import ssl
import struct
import tempfile
import traceback

from libpebble2.communication.transports.qemu import MessageTargetQemu
from libpebble2.services.install import AppInstaller

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
    def __init__(self, qemu, pbws, port, token=None, ssl_root=None, persist_dir=None, oauth_token=None,
                 layout_file=None):
        self.port = port
        self.token = token
        self.requires_auth = (token is not None)
        self.authed = not self.requires_auth
        self.server = None
        self.websockets = []
        self.ssl_root = ssl_root
        self.config_callback = None
        super(WebsocketRunner, self).__init__(qemu, pbws, persist_dir=persist_dir, oauth_token=oauth_token, layout_file=layout_file)

    def run(self):
        pebble_greenlet = self.pebble.connect()
        self.pebble.pebble.register_raw_inbound_handler(self._handle_inbound)
        self.pebble.pebble.register_raw_outbound_handler(self._handle_outbound)
        if self.pebble.timeline_is_supported:
            self.timeline.continuous_sync()
            self.timeline.do_maintenance()
        logging.getLogger().addHandler(WebsocketLogHandler(self, level=logging.WARNING))
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
        gevent.spawn(self.server.serve_forever)
        pebble_greenlet.join()
        self.server.close()
        self.pebble.disconnect()

    def log_output(self, message):
        self.broadcast(bytearray('\x02' + message.encode('utf-8')))

    def open_config_page(self, url, callback):
        self.broadcast(bytearray(struct.pack('>BBI%ds' % len(url), 0x0a, 0x01, len(url), url)))
        self.config_callback = callback

    def _handle_outbound(self, message):
        self.broadcast(bytearray('\x01' + message))

    def _handle_inbound(self, message):
        self.broadcast(bytearray('\x00' + message))

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
        if ws in self.websockets:
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
            self.logger.debug("not a bytearray")
            self.logger.debug("received: %s", message)
            return
        opcode = message[0]
        opcode_handlers = {
            0x01: self.do_relay,
            0x04: self.do_install,
            0x06: self.do_phone_info,
            0x09: self.do_auth,
            0x0a: self.do_config_ws,
            0x0b: self.do_qemu_command,
            0x0c: self.do_timeline_command,
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
        self.pebble.pebble.send_raw(str(message))

    @must_auth
    def do_install(self, ws, message):
        def go_do_install():
            with tempfile.NamedTemporaryFile() as f:
                f.write(message)
                f.flush()
                try:
                    self.load_pbws([f.name], cache=True)
                    AppInstaller(self.pebble.pebble, f.name, blobdb_client=self.pebble.blobdb).install()
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

    @must_auth
    def do_qemu_command(self, ws, message):
        protocol = message[0]
        self.pebble.pebble.transport.send_packet(str(message[1:]),
                                                 target=MessageTargetQemu(protocol=protocol, raw=True))

    @must_auth
    def do_timeline_command(self, ws, message):
        command = message[0]
        message = str(message[1:])
        try:
            if command == 0x01:
                try:
                    pin = json.loads(message)
                except ValueError:
                    ws.send(bytearray([0x0c, 0x01]))
                    return
                self.timeline.handle_pin_create(pin, manual=True)
                ws.send(bytearray([0x0c, 0x00]))
            elif command == 0x02:
                self.timeline.handle_pin_delete({'guid': message})
        except Exception as e:
            traceback.print_exc()
            self.log_output("Pin insert failed: %s: %s" % (type(e).__name__, e.message))
            ws.send(bytearray([0x0c, 0x01]))


class WebsocketLogHandler(logging.Handler):
    def __init__(self, ws_runner, *args, **kwargs):
        self.ws_runner = ws_runner
        logging.Handler.__init__(self, *args, **kwargs)
        self.setFormatter(logging.Formatter("[PHONESIM] [%(levelname)s] %(message)s"))

    def emit(self, record):
        self.ws_runner.log_output(self.format(record))
