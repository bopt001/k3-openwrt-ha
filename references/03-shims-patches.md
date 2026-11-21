# Phase 3 — Pure-Python shims and source patches

This is the reusable core of the whole effort. A 32-bit ARM musl box with no
compiler cannot install Rust/C extension wheels. The workaround: replace each
compiled dependency with a small pure-Python module that satisfies the import
surface HA actually uses, plus fake package metadata so HA stops trying to
re-install it.

## 3.1 The five shims (source in `scripts/shims/`)

| Package | Why it fails | Shim strategy |
|---|---|---|
| `orjson` | Rust wheel, no musl/armv7 build | `json`-based `dumps`/`loads`, option constants, `Fragment` |
| `lru` | C extension | `OrderedDict`-backed `LRU` with `get/set_size/clear` |
| `aiohttp_zlib_ng` | compiled zlib-ng binding | no-op `enable_zlib_ng()` |
| `fnv_hash_fast` | C extension | pure-Python FNV-1a / FNV-1 32-bit |
| `numpy` | compiled BLAS/Lua-free numeric core | no-op `fliplr/flipud/rot90/asarray` + dtype constants |

### Fake dist-info (mandatory)

For each shim, create e.g.
`/usr/lib/python3.11/site-packages/orjson-3.9.15.dist-info/METADATA`:

```
Metadata-Version: 2.1
Name: orjson
Version: 3.9.15
```

Without this, HA detects a missing requirement and re-enters the pip-install
loop (which cannot compile and wedges the machine).

### The `orjson.Fragment` trap (a real post-reboot crash)

`orjson.Fragment` wraps *already-serialized JSON* and must be embedded verbatim.
A naive shim that stores the object and lets `json.dumps` hit `str(o)` writes
`"<orjson.Fragment object at 0x...>"` into HA's `.storage/` files.
`homeassistant/helpers/restore_state.py` then does
`item["state"]["entity_id"]` on that string and the whole startup dies with
`TypeError: string indices must be integers, not 'str'`.

The shipped `orjson/__init__.py` handles this correctly: `Fragment.__init__`
`json.loads`-es bytes/str back into a real Python object, and `dumps()` runs a
recursive `prep()` pass that unwraps nested Fragments before handing off to the
stdlib encoder.

**General lesson:** when shimming a serialization library, the output must always
be valid JSON values. Silent corruption only shows up after the next reboot.

### The `numpy` shim (endless "Loading data")

The websocket API's selector validation calls `_entity_features()`, which imports
`homeassistant.components.camera`, which imports `stream.core`, which does
`import numpy as np`. Those `np.*` calls are only image-flip helpers inside
lambdas that never execute for normal use. A no-op shim is enough; verify with:

```sh
python3 -c "from homeassistant.components.camera import CameraEntityFeature; print('OK')"
```

## 3.2 Three source patches

### Patch A — aiohttp 3.9 API on aiohttp 3.8.5

Symptom: 8123 LISTEN but requests time out / empty reply; log shows
`TypeError: RequestHandler.__init__() got unexpected keyword argument
'handler_cancellation'`, then `shutdown_timeout`.

File: `/usr/lib/python3.11/site-packages/homeassistant/components/http/__init__.py`
(around line 521). Replace:

```python
self.runner = web.AppRunner(self.app, handler_cancellation=True, shutdown_timeout=10)
```

with:

```python
self.runner = web.AppRunner(self.app)
```

Then delete `__pycache__/__init__.cpython-311.pyc` and restart. This patch is
overwritten if HA components or aiohttp are ever reinstalled — re-apply it.

### Patch B — `Fragment` fix inside the orjson shim

Described in 3.1; already applied in `scripts/shims/orjson/__init__.py`.

### Patch C — OOM watermark in the init script

`/etc/init.d/homeassistant` sets `min_free_kbytes=8192`, `drop_caches=3` and
`compact_memory=1` **before** launching `hass --skip-pip --config
/etc/homeassistant`. See `scripts/homeassistant.initd`.

## 3.3 Deploying the shims

```sh
SP=/usr/lib/python3.11/site-packages
# copy each scripts/shims/<name>/__init__.py to $SP/<name>/__init__.py
# create the matching <name>-<ver>.dist-info/METADATA
# remove stale __pycache__ for the shims and for the HA modules you patched
rm -f $SP/orjson/__pycache__/init.cpython-311.pyc
/etc/init.d/homeassistant restart
```

Verify imports one by one before restarting HA — a broken shim is much easier to
diagnose at the Python prompt than through HA's bootstrap.
