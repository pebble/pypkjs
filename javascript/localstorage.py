__author__ = 'katharine'

import PyV8 as v8

_storage_cache = {}

class LocalStorage(object):
    def __init__(self, runtime):
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
        return self.storage.get(name, v8.JSNull())

    def set(self, p, name, value):
        self.storage[str(name)] = str(value)
        #TODO: actually store this somewhere.
        return True

    def has(self, p, name):
        return name in self.storage

    def delete_(self, p, name):
        if name in self.storage:
            del self.storage[name]
            #TODO: actually store this somewhere.
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
        return self.storage.get(name, v8.JSNull())

    def setItem(self, name, value, *args):
        self.set(None, name, value)

    def removeItem(self, name, *args):
        return self.delete_(None, name)

    def key(self, index, *args):
        if len(self.storage) > index:
            return self.storage.keys()[index]
        else:
            return v8.JSNull()
