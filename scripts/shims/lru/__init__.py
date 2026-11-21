"""Pure-Python LRU shim compatible with the `lru` C extension API used by HA."""
from collections import OrderedDict

class LRU:
    def __init__(self, size):
        self._data = OrderedDict()
        self._size = size

    def __class_getitem__(cls, item):
        return cls

    def get(self, key, default=None):
        try:
            value = self._data.pop(key)
        except KeyError:
            return default
        self._data[key] = value
        return value

    def __getitem__(self, key):
        value = self._data.pop(key)
        self._data[key] = value
        return value

    def __setitem__(self, key, value):
        if key in self._data:
            del self._data[key]
        self._data[key] = value
        while len(self._data) > self._size:
            self._data.popitem(last=False)

    def __contains__(self, key):
        return key in self._data

    def __len__(self):
        return len(self._data)

    def get_size(self):
        return self._size

    def set_size(self, size):
        self._size = size
        while len(self._data) > self._size:
            self._data.popitem(last=False)

    def clear(self):
        self._data.clear()
