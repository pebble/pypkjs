__author__ = 'katharine'

import PyV8 as v8
import array
import struct


class ArrayBuffer(v8.JSClass):
    def __init__(self, length):
        self._array = array.array('B', [0] * length)
        self.length = 1


class TypedArray(v8.JSClass):
    def __init__(self, param, *more_params):
        super(TypedArray, self).__init__()
        self._offset = 0
        if isinstance(param, int):
            self._buffer = ArrayBuffer(param * self._width)
            self._length = param
        elif isinstance(param, TypedArray):
            self._length = len(param.buffer._array) // param._width
            self._buffer = ArrayBuffer(self._length * self._width)
            self._buffer._array = param._buffer._array[:]
        elif isinstance(param, ArrayBuffer):
            self._buffer = param
            self._length = len(param._array) // self._width
            if len(more_params) >= 1:
                if more_params[0] is not None:
                    self._offset = more_params[0]
                if len(more_params) >= 2:
                    if more_params[1] is not None:
                        self._length = more_params[1]

    def __getitem__(self, item):
        if not isinstance(item, int):
            raise TypeError("should be an int")
        if item > self._length:
            raise IndexError("too big")
        index = self._offset + item * self._width
        return struct.unpack_from('<' + self._kind, self._buffer._array, index)[0]

    @property
    def buffer(self):
        return self._buffer

    @property
    def byteLength(self):
        return self._length * self._width

    @property
    def byteOffset(self):
        return self._offset

    @property
    def length(self):
        return self._length



    def __len__(self):
        return self.length


class Uint8Array(TypedArray):
    def __init__(self, *args):
        self._kind = 'B'
        self._width = 1
        self.name = "Uint8Array"
        TypedArray.__init__(self, *args)


class Int8Array(TypedArray):
    def __init__(self, *args):
        self._kind = 'b'
        self._width = 1
        self.name = "Int8Array"
        TypedArray.__init__(self, *args)


class Uint16Array(TypedArray):
    def __init__(self, *args):
        self._kind = 'H'
        self._width = 2
        self.name = "Uint16Array"
        TypedArray.__init__(self, *args)


class Int16Array(TypedArray):
    def __init__(self, *args):
        self._kind = 'h'
        self._width = 2
        self.name = "Int16Array"
        TypedArray.__init__(self, *args)


class Uint32Array(TypedArray):
    def __init__(self, *args):
        self._kind = 'I'
        self._width = 4
        self.name = "Uint32Array"
        TypedArray.__init__(self, *args)


class Int32Array(TypedArray):
    def __init__(self, *args):
        self._kind = 'i'
        self._width = 4
        self.name = "Int32Array"
        TypedArray.__init__(self, *args)
