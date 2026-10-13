#!/bin/sh
# Build falcon-engine_<version>_all.deb from this checkout (run on Linux, from the repository root):
#
#     sh installers/engine/build_deb.sh [out-dir] [wheels-dir]
#
# The package carries the Engine's payload (installers/payload.py, with a manifest of hashes) under /opt/falcon/payload and the command
# `falcon-engine-install`. A wheels folder makes the install work with no network.
set -eu

out="${1:-dist}"
wheels="${2:-}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"

version="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

mkdir -p "$stage/DEBIAN" "$stage/opt/falcon" "$stage/usr/sbin"
if [ -n "$wheels" ]; then
    python3 -m installers.payload engine "$stage/opt/falcon/payload" --wheels "$wheels"
else
    python3 -m installers.payload engine "$stage/opt/falcon/payload"
fi

sed "s/@VERSION@/$version/" installers/engine/debian/control > "$stage/DEBIAN/control"
for script in postinst prerm postrm; do
    install -m 0755 "installers/engine/debian/$script" "$stage/DEBIAN/$script"
done

cat > "$stage/usr/sbin/falcon-engine-install" <<'WRAPPER'
#!/bin/sh
cd /opt/falcon/payload
exec python3 -m installers.engine.install --source /opt/falcon/payload "$@"
WRAPPER
chmod 0755 "$stage/usr/sbin/falcon-engine-install"

mkdir -p "$out"
dpkg-deb --root-owner-group --build "$stage" "$out/falcon-engine_${version}_all.deb"
echo "built $out/falcon-engine_${version}_all.deb"
