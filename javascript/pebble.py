__author__ = 'katharine'

import collections
import struct
import itertools
from uuid import UUID

import PyV8 as v8
from pebblecomm.pebble import Pebble as PebbleComm, AppMessage, Notification, Attribute

import events
from exceptions import JSRuntimeException


class Pebble(events.EventSourceMixin, v8.JSClass):
    def __init__(self, runtime, pebble):
        self.extension = v8.JSExtension(runtime.ext_name("pebble"), """
        Pebble = new (function() {
            native function _internal_pebble();
            _make_proxies(this, _internal_pebble(),
                ['sendAppMessage', 'showSimpleNotificationOnPebble', 'getAccountToken', 'getWatchToken',
                'addEventListener', 'removeEventListener', 'openURL']);
        })();
        """, lambda f: lambda: self, dependencies=["runtime/internal/proxy"])
        self.pebble = pebble.pebble
        self.runtime = runtime
        self.tid = 0
        self.uuid = UUID(runtime.manifest['uuid'])
        self.app_keys = runtime.manifest['appKeys']
        self.pending_acks = {}
        self.is_ready = False
        super(Pebble, self).__init__(runtime)

    def _connect(self):
        self._ready()

    def _ready(self):
        self.pebble.register_endpoint("APPLICATION_MESSAGE", self._handle_appmessage)
        self.is_ready = True
        self.triggerEvent("ready")

    def _shutdown(self):
        self.pebble.register_endpoint("APPLICATION_MESSAGE", lambda a, b: False)  # ffs libpebble.

    def _configure(self):
        self.triggerEvent("showConfiguration")

    def _handle_appmessage(self, endpoint, data):
        command, tid = struct.unpack_from("BB", data, 0)
        if command in (0x7f, 0xff):
            self._handle_ack(command, tid)
        elif command == 0x01:
            target_uuid = UUID(bytes=data[2:18])
            self._handle_message(tid, target_uuid, data[18:])

    def _handle_ack(self, command, tid):
        try:
            success, failure = self.pending_acks[tid]
        except KeyError:
            return
        callback_param = {"data": {"transactionId": tid}}
        if command == 0x7f:  # NACK
            callback_param['data']['error'] = 'Something went wrong.'
            if callable(failure):
                self.runtime.enqueue(failure, callback_param)
        elif command == 0xff:  # ACK
            if callable(success):
                self.runtime.enqueue(success, callback_param)
        del self.pending_acks[tid]

    def _handle_message(self, tid, uuid, encoded_dict):
        if uuid != self.uuid:
            print "Discarded message for %s (expected %s)" % (uuid, self.uuid)
            self.pebble._send_message("APPLICATION_MESSAGE", struct.pack('<BB', 0x7F, tid))  # ACK
            return
        app_keys = dict(zip(self.app_keys.values(), self.app_keys.keys()))
        try:
            tuple_count, = struct.unpack_from('<B', encoded_dict, 0)
            offset = 1
            d = self.runtime.context.eval("({})")  # This is kinda absurd.
            for i in xrange(tuple_count):
                k, t, l = struct.unpack_from('<IBH', encoded_dict, offset)
                offset += 7
                if t == 0:  # BYTE_ARRAY
                    v = v8.JSArray(list(struct.unpack_from('<%dB' % l, encoded_dict, offset)))
                elif t == 1:  # CSTRING
                    v, = struct.unpack_from('<%ds' % l, encoded_dict, offset)
                    try:
                        v = v[:v.index('\x00')]
                    except ValueError:
                        pass
                elif t in (2, 3):  # UINT, INT
                    widths = {
                        (2, 1): 'B',
                        (2, 2): 'H',
                        (2, 4): 'I',
                        (3, 1): 'b',
                        (3, 2): 'h',
                        (3, 4): 'i',
                    }
                    v, = struct.unpack_from('<%s' % widths[(t, l)], encoded_dict, offset)
                else:
                    raise Exception("Received bad appmessage dict.")
                d[str(k)] = v
                if k in app_keys:
                    d[str(app_keys[k])] = v
                offset += l
        except:
            self.pebble._send_message("APPLICATION_MESSAGE", struct.pack('<BB', 0x7F, tid))  # NACK
            raise
        else:
            self.pebble._send_message("APPLICATION_MESSAGE", struct.pack('<BB', 0xFF, tid))  # ACK
            e = events.Event(self.runtime, "AppMessage")
            e.payload = d
            self.triggerEvent("appmessage", e)

    def _check_ready(self):
        if not self.is_ready:
            raise JSRuntimeException("Can't interact with the watch before the ready event is fired.")

    def sendAppMessage(self, message, success=None, failure=None):
        self._check_ready()
        to_send = {}
        message = {k: message[str(k)] for k in message.keys()}
        for k, v in message.iteritems():
            if k in self.app_keys:
                k = self.app_keys[k]
            try:
                to_send[int(k)] = v
            except ValueError:
                raise JSRuntimeException("Unknown message key '%s'" % k)

        tuples = []
        appmessage = AppMessage()
        for k, v in to_send.iteritems():
            if isinstance(v, v8.JSArray):
                v = list(v)
            if isinstance(v, basestring):
                t = "CSTRING"
                v += '\x00'
            elif isinstance(v, int):
                t = "INT"
                v = struct.pack('<i', v)
            elif isinstance(v, float):  # thanks, javascript
                t = "INT"
                try:
                    intv = int(round(v))
                except ValueError:
                    self.runtime.log_output("WARNING: illegal float value %s for appmessage key %s" % (v, k))
                    intv = 0
                v = struct.pack('<i', intv)
            elif isinstance(v, collections.Sequence):
                t = "BYTE_ARRAY"
                fmt = ['<']
                for byte in v:
                    if isinstance(byte, int):
                        if 0 <= byte <= 255:
                            fmt.append('B')
                        else:
                            raise JSRuntimeException("Bytes must be between 0 and 255 inclusive.")
                    elif isinstance(byte, str):  # This is intentionally not basestring; unicode won't work.
                        fmt.append('%ss' % len(byte))
                    else:
                        raise JSRuntimeException("Unexpected value in byte array.")
                v = struct.pack(''.join(fmt), *v)
            elif v is None:
                continue
            else:
                raise JSRuntimeException("Invalid value data type for key %s: %s" % (k, type(v)))
            tuples.append(appmessage.build_tuple(k, t, v))

        d = appmessage.build_dict(tuples)
        message = appmessage.build_message(d, "PUSH", self.uuid.bytes, struct.pack('B', self.tid))
        self.pending_acks[self.tid] = (success, failure)
        self.tid = (self.tid + 1) % 256
        self.pebble._send_message("APPLICATION_MESSAGE", message)

    def showSimpleNotificationOnPebble(self, title, message):
        self._check_ready()
        notification = Notification(self.pebble, title, attributes=[Attribute("BODY", message)])
        notification.send()

    def showNotificationOnPebble(self, opts):
        pass

    def getAccountToken(self):
        self._check_ready()
        return "0123456789abcdef0123456789abcdef"

    def getWatchToken(self):
        self._check_ready()
        return "0123456789abcdef0123456789abcdef"

    def openURL(self, url):
        self.runtime.open_config_page(url, self._handle_config_response)

    def _handle_config_response(self, response):
        def go():
            e = events.Event(self.runtime, "WebviewClosed")
            e.response = response
            self.triggerEvent("webviewclosed", e)
        self.runtime.enqueue(go)
