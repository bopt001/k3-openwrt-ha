"""Pure-Python fallback shim for orjson on musl/armv7 where the Rust wheel cannot run."""
import json as _json
from json import JSONDecodeError

OPT_SERIALIZE_NUMPY = 1
OPT_SERIALIZE_DATACLASS = 2
OPT_SERIALIZE_UUID = 4
OPT_NAIVE_UTC = 8
OPT_NON_STR_KEYS = 16
OPT_INDENT_2 = 32
OPT_SORT_KEYS = 64
OPT_APPEND_NEWLINE = 128
OPT_PASSTHROUGH_DATACLASS = 256
OPT_PASSTHROUGH_DATETIME = 512
OPT_PASSTHROUGH_SUBCLASS = 1024
OPT_SERIALIZE_SUBCLASS = 2048
OPT_STRICT_INTEGER = 4096
OPT_REPLACE_INVALID_UTF8 = 8192
OPT_UTC_Z = 16384

class Fragment:
    """orjson.Fragment wraps already-serialized JSON. Unwrap it back to a
    plain Python object so the stdlib json encoder emits a real JSON value
    instead of the object repr (which corrupted HA's .storage files)."""
    def __init__(self, value):
        if isinstance(value, (bytes, bytearray, str)):
            try:
                value = _json.loads(value)
            except (ValueError, TypeError):
                pass
        self.value = value

def _unwrap(o):
    if isinstance(o, Fragment):
        return o.value
    return o

def dumps(obj, default=None, option=None, **kwargs):
    def enc(o):
        if isinstance(o, Fragment):
            return _unwrap(o)
        if default is not None:
            try:
                return default(o)
            except (TypeError, ValueError):
                pass
        return str(o)
    sort = bool(option and (option & OPT_SORT_KEYS))
    indent = 2 if (option and (option & OPT_INDENT_2)) else None
    # Pre-unwrap top-level / nested Fragment values via a recursive pass, because
    # json's default() is only called for objects it cannot encode natively.
    def prep(o):
        if isinstance(o, Fragment):
            return prep(o.value)
        if isinstance(o, dict):
            return {k: prep(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [prep(v) for v in o]
        return o
    return _json.dumps(prep(obj), default=enc, separators=(",", ":"), sort_keys=sort, indent=indent).encode("utf-8")

def loads(data, **kwargs):
    if isinstance(data, (bytes, bytearray)):
        data = bytes(data).decode("utf-8")
    return _json.loads(data)
