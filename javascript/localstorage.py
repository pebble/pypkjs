__author__ = 'katharine'

import PyV8 as v8


class LocalStorage(object):
    def __init__(self, runtime):
        self.storage = {}
        self.extension = v8.JSExtension(runtime.ext_name("localstorage"), """
        (function() {
            native function _internal_storage();

            var internal = new (function() {
                _make_proxies(this, _internal_storage(), ['get', 'set', 'has', 'delete', 'keys', 'enumerate', 'clear',
                                                            'getItem', 'setItem', 'removeItem', 'key']);
                var realGet = this.get;
                var self = this;
                this.get = function(p, name) { return self[name] || realGet(p, name); };
            })();

            this.localStorage = Proxy.create(internal);
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

    def delete(self, p, name):
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
        return self.delete(None, name)

    def key(self, index, *args):
        if len(self.storage) > index:
            return self.storage.keys()[index]
        else:
            return v8.JSNull()
