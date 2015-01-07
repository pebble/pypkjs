__author__ = 'katharine'

import PyV8 as v8


class LocalStorage(object):
    def __init__(self, runtime):
        self.storage = {}
        self.extension = v8.JSExtension(runtime.ext_name("localstorage"), """
        (function() {
            native function _get();
            native function _set();
            native function _has();
            native function _delete();
            native function _enumerate();
            native function _keys();
            native function _clear();
            native function _getItem();
            native function _setItem();
            native function _removeItem();
            native function _key();

            var methodMappings = {
                clear: function() { _clear(); },
                getItem: function(key) { return _getItem(key); },
                setItem: function(key, value) { return _setItem(key, value); },
                removeItem: function(key) { return _removeItem(key); },
                key: function(index) { return _key(index); },
            }

            this.localStorage = Proxy.create({
                get: function(p, name) { return methodMappings[name] || _get(name); },
                set: function(p, name, value) { return _set(name, value) },
                has: function(p, name) { return _has(name) },
                delete: function(p, name) { return _delete(name) },
                enumerate: function(p) { return _enumerate() },
                keys: function(p, name) { return _keys(name) },
            });
        })();
        """, lambda f: getattr(self, 'proxy%s' % f))

    def proxy_get(self, name):
        if hasattr(self, "instance_%s" % name):
            return getattr(self, "instance_%s" % name)
        return self.storage.get(name, v8.JSNull())

    def proxy_set(self, name, value):
        self.storage[str(name)] = str(value)
        #TODO: actually store this somewhere.
        return True

    def proxy_has(self, name):
        return name in self.storage

    def proxy_delete(self, name):
        if name in self.storage:
            del self.storage[name]
            #TODO: actually store this somewhere.
            return True
        else:
            return False

    def proxy_keys(self):
        return self.storage.keys()

    def proxy_enumerate(self):
        return self.storage.keys()

    def proxy_clear(self):
        self.storage.clear()

    def proxy_getItem(self, name):
        return self.storage.get(name, v8.JSNull())

    def proxy_setItem(self, name, value):
        self.proxy_set(name, value)

    def proxy_removeItem(self, name):
        return self.proxy_delete(name)

    def proxy_key(self, index):
        if len(self.storage) > index:
            return self.storage.keys()[index]
        else:
            return v8.JSNull()
