#!/bin/sh
# Deploy the five pure-Python shims onto a K3/OpenWrt device.
# Run ON THE DEVICE, from the directory containing scripts/shims/.
# Idempotent: backs up nothing, but never overwrites a real installed package.
set -e

SP=/usr/lib/python3.11/site-packages
SRC=$(dirname "$0")/shims

# name|version  -- keep versions in sync with the fake dist-info metadata
SHIMS="orjson|3.9.15 lru|0.1 aiohttp_zlib_ng|0.1 fnv_hash_fast|0.1 numpy|1.26.0"

for entry in $SHIMS; do
  name=${entry%%|*}
  ver=${entry#*|}
  target="$SP/$name"
  if [ -d "$target" ] && [ ! -f "$target/.k3_shim" ]; then
    echo "SKIP $name: a real package appears to be installed at $target"
    continue
  fi
  mkdir -p "$target"
  cp "$SRC/$name/__init__.py" "$target/__init__.py"
  touch "$target/.k3_shim"

  di="$SP/$name-$ver.dist-info"
  mkdir -p "$di"
  cat > "$di/METADATA" << EOF
Metadata-Version: 2.1
Name: $name
Version: $ver
Summary: Pure-Python shim for musl/armv7 OpenWrt (no compiler available)
EOF
  echo "installed $name==$ver (shim + dist-info)"
done

# Drop stale bytecode for shims and patched HA modules
find "$SP/orjson" "$SP/lru" "$SP/numpy" -name "*.pyc" -delete 2>/dev/null || true
rm -f "$SP/homeassistant/components/http/__pycache__/__init__.cpython-311.pyc" 2>/dev/null || true
rm -f "$SP/homeassistant/helpers/__pycache__/restore_state.cpython-311.pyc" 2>/dev/null || true
rm -f "$SP/homeassistant/helpers/__pycache__/json.cpython-311.pyc" 2>/dev/null || true

echo "Done. Verify imports before restarting HA:"
echo "  python3 -c 'import orjson, lru, numpy, fnv_hash_fast, aiohttp_zlib_ng; print(\"shims OK\")'"
echo "  python3 -c 'from homeassistant.components.camera import CameraEntityFeature; print(\"camera OK\")'"
echo "Then: /etc/init.d/homeassistant restart"
