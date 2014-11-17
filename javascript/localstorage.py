__author__ = 'katharine'

import PyV8 as v8


class LocalStorage(v8.JSClass):
    def __init__(self):
        object.__setattr__(self, 'values', {})
        v8.JSClass.__init__(self)

    def __setattr__(self, key, value):
        object.__getattribute__(self, 'values')[key] = value
        pass

    def __delattr__(self, item):
        try:
            del object.__getattribute__(self, 'values')[item]
        except KeyError:
            pass

    def __getattribute__(self, item):
        if item in ("getItem", "setItem", "removeItem", "key", "clear", "__watchpoints__", "length"):
            return object.__getattribute__(self, item)
        try:
            return object.__getattribute__(self, 'values')[item]
        except KeyError:
            return None

    def __iter__(self):
        for key in object.__getattribute__(self, 'values'):
            yield key

    def __len__(self):
        return len(object.__getattribute__(self, 'values'))

    def getItem(self, item):
        return object.__getattribute__(self, 'values').get(item, None)

    def setItem(self, key, value):
        object.__getattribute__(self, 'values')[key] = value

    def removeItem(self, key):
        try:
            del object.__getattribute__(self, 'values')[key]
        except KeyError:
            pass

    def clear(self):
        object.__getattribute__(self, 'values').clear()

    def key(self, index):
        try:
            return object.__getattribute__(self, 'values').keys()[index]
        except IndexError:
            return None

    @property
    def length(self):
        return len(self)
