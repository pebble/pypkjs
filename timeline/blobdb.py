__author__ = 'katharine'

import collections
import gevent
import gevent.queue
import logging
import random
import struct
import time
import uuid


class BlobDB(object):
    DB_TEST = 0
    DB_PIN = 1
    DB_APP = 2
    DB_REMINDER = 3
    DB_NOTIFICATION = 4

    _PendingItem = collections.namedtuple('_PendingItem', ('token', 'data', 'callback'))
    _PendingAck = collections.namedtuple('_PendingAck', ('timestamp', 'data', 'callback'))

    RESPONSE_CODES = {
        0x01: "SUCCESS",
        0x02: "GENERAL_FAILURE",
        0x03: "INVALID_OPERATION",
        0x04: "INVALID_DATABASE_ID",
        0x05: "INVALID_DATA",
        0x06: "KEY_DOES_NOT_EXIST",
        0x07: "DATABASE_FULL",
        0x08: "DATA_STALE",
    }

    def __init__(self, pebble):
        self.pebble = pebble
        self.logger = logging.getLogger('pypkjs.timeline.blobdb')
        self.pending_ack = collections.OrderedDict()
        self.active_tokens = set()
        self.queue = gevent.queue.Queue()
        self.running = True
        self.pebble.register_endpoint("BLOB_DB", self.handle_blob_db, preprocess=False)

    def _enqueue(self, item):
        self.queue.put(item)

    def _get_token(self):
        while True:
            token = random.randrange(1, 2**16 - 1, 1)
            # Cooperative threading says this is safe.
            if token not in self.active_tokens:
                self.active_tokens.add(token)
                return token

    @staticmethod
    def _key_bytes(key):
        return uuid.UUID(key).bytes

    def insert(self, database, key, value, callback=None):
        token = self._get_token()
        key = self._key_bytes(key)
        value = value
        self.logger.debug('queued insertion %s', token)
        data = struct.pack("<BHBB%dsH%ds" % (len(key), len(value)),
                           0x01, token, database, len(key), key, len(value), value)
        self._enqueue(self._PendingItem(token, data, callback))

    def delete(self, database, key, callback=None):
        token = self._get_token()
        key = self._key_bytes(key)
        data = struct.pack("<BHBB%ds" % len(key), 0x04, token, database, len(key), key)
        self._enqueue(self._PendingItem(token, data, callback))

    def clear(self, database, callback=None):
        token = self._get_token()
        data = struct.pack("<BHB", 0x05, token, database)
        self._enqueue(self._PendingItem(token, data, callback))

    def handle_blob_db(self, endpoint, data):
        data.encode('hex')
        token, code = struct.unpack("<HB", data)
        if token in self.pending_ack:
            self.logger.debug('got response for known token %s', token)
            pending = self.pending_ack[token]
            del self.pending_ack[token]
            self.active_tokens.remove(token)
            if callable(pending.callback):
                pending.callback(code)

    def run(self):
        gevent.spawn(self.check_pending_acks)
        gevent.spawn(self.send_queued_data)

    def stop(self):
        self.running = False
        self.queue.put(StopIteration)

    def check_pending_acks(self):
        self.logger.debug('check_pending_acks running')
        while self.running:
            now = time.time()
            for token, pending in self.pending_ack.items():
                if now - pending.timestamp > 5:
                    # Give up and retry.
                    self.logger.info("timed out; retrying %d", token)
                    del self.pending_ack[token]
                    self._enqueue(self._PendingItem(token, pending.data, pending.callback))
            gevent.sleep(5)

    def send_queued_data(self):
        self.logger.debug('send_queued_data running')
        for token, data, callback in self.queue:
            self.logger.debug('got message to send: %s', token)
            self.pending_ack[token] = self._PendingAck(time.time(), data, callback)
            self.pebble._send_message("BLOB_DB", data)
            gevent.sleep(0.05)  # To prevent excessive spam.

    @classmethod
    def stringify_error_code(cls, code):
        return cls.RESPONSE_CODES.get(code, hex(code))
