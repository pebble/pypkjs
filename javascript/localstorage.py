__author__ = 'katharine'

import PyV8 as v8


class LocalStorage(object):
    def __init__(self, runtime):
        self.extension = v8.JSExtension(runtime.ext_name("localstorage"), """
        localStorage = Object.create({}, {
            getItem: {
                value: function(item) {
                    var value = localStorage[item];
                    if(value === undefined) {
                        return null;
                    } else {
                        return value;
                    }
                }
            },
            setItem: {
                value: function(item, value) {
                    localStorage[item] = String(value);
                }
            },
            removeItem: {
                value: function(item) {
                    delete localStorage[item];
                }
            },
            clear: {
                value: function() {
                    for(var obj in localStorage) {
                        delete localStorage[obj];
                    }
                }
            },
            key: {
                value: function(i) {
                    return Object.keys(localStorage)[i];
                }
            },
            length: {
                value: function() {
                    return Object.keys(localStorage).length;
                }
            }
        });

        (function() {
            native function _save_key();
            native function _delete_key();
            Object.observe(localStorage, function(changes) {
                changes.forEach(function(change) {
                    var key = change.name;
                    if(change == 'add' || change == 'update') {
                        if(key in localStorage) {
                            if(typeof(value) != "string") {
                                localStorage[key] = String(localStorage[key]);
                            }
                            _save_key(key, localStorage[key]);
                        }
                    } else if(change == 'delete') {
                        _delete_key(key);
                    }
                });
            });
        })();
        """, lambda f: getattr(self, 'js%s' % f))

    def js_save_key(self, key, value):
        pass

    def js_delete_key(self, key):
        pass
