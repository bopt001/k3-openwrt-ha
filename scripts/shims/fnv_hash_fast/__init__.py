"""Pure-Python shim for fnv-hash-fast on musl/armv7."""
def fnv1a_32(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    h = 2166136261
    for b in data:
        h ^= b
        h = (h * 16777619) & 0xFFFFFFFF
    return h

def fnv1_32(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    h = 2166136261
    for b in data:
        h = (h * 16777619) & 0xFFFFFFFF
        h ^= b
    return h & 0xFFFFFFFF

fnv1a_64 = fnv1a_32
fnv1_64 = fnv1_32
