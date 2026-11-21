def enable_zlib_ng():
    """No-op shim: optional aiohttp zlib-ng acceleration unavailable on musl/armv7."""
    return False
