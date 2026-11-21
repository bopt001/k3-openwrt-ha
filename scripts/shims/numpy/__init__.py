"""Minimal numpy shim for musl/armv7 K3 where no numpy wheel exists.
Only needs to satisfy imports and a handful of image-flip helpers used by
HA's stream component; real numeric work is not expected on this device.
"""
__version__ = "1.26.0-shim"

def _identity(x, *a, **k):
    return x

def fliplr(x):
    try:
        return x[:, ::-1]
    except Exception:
        return x

def flipud(x):
    try:
        return x[::-1]
    except Exception:
        return x

def rot90(x, k=1):
    return x

def asarray(x, *a, **k):
    return x

def array(x, *a, **k):
    return x

def ndarray(*a, **k):
    return None

class ndarray_type:
    pass

# common attributes referenced at import time
uint8 = "uint8"
float32 = "float32"
float64 = "float64"
int32 = "int32"
