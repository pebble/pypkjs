from __future__ import absolute_import
__author__ = 'katharine'

import pypkjs.PyV8 as v8
import errno
import logging
import os
import os.path
import dumbdbm  # This is the only one that actually syncs data if the process dies before I can close().
logger = logging.getLogger("pypkjs.javascript.localstorage")

_storage_cache = {}  # This is used when filesystem-based storage is unavailable.


class LocalStorage(object):
    def __init__(self, runtime, persist_dir=None):
        self.storage = None
        if persist_dir is not None:
            try:
                try:
                    os.makedirs(os.path.join(persist_dir, 'localstorage'))
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise

                self.storage = dumbdbm.open(os.path.join(persist_dir, 'localstorage', runtime.manifest['uuid']), 'c')
            except IOError:
                pass
        if self.storage is None:
            logger.warning("Using transient store.")
            self.storage = _storage_cache.setdefault(runtime.manifest['uuid'], {})

        self.extension = v8.JSExtension(runtime.ext_name("localstorage"), """
        (function() {
            native function _internal();

            var proxy = _make_proxies({}, _internal(), ['set', 'has', 'delete_', 'keys', 'enumerate']);
            var methods = _make_proxies({}, _internal(), ['clear', 'getItem', 'setItem', 'removeItem', 'key']);
            proxy.get = function get(p, name) { return methods[name] || _internal().get(p, name); }

            this.localStorage = Proxy.create(proxy);
        })();
        """, lambda f: lambda: self, dependencies=["runtime/internal/proxy"])

    def get(self, p, name):
        return self.storage.get(str(name), v8.JSNull())

    def set(self, p, name, value):
        self.storage[str(name)] = str(value)
        return True

    def has(self, p, name):
        return name in self.storage

    def delete_(self, p, name):
        if name in self.storage:
            del self.storage[name]
            return True
        else:
            return False

    def keys(self, p):
        return v8.JSArray(self.storage.keys())

    def enumerate(self):
        return v8.JSArray(self.storage.keys())

    def clear(self, *args):
        self.storage.clear()

    def getItem(self, name, *args):
        return self.get(None, name)

    def setItem(self, name, value, *args):
        self.set(None, name, value)

    def removeItem(self, name, *args):
        return self.delete_(None, name)

    def key(self, index, *args):
        if len(self.storage) > index:
            return self.storage.keys()[index]
        else:
            return v8.JSNull()

    def _shutdown(self):
        if hasattr(self.storage, 'close'):
            self.storage.close()
