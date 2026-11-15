#!/bin/sh
# Build falcon-engine_<version>_<arch>.deb from this checkout (run on Linux, from the repository root):
#
#     sh installers/engine/build_deb.sh [out-dir] [wheels-dir]          (PG_VERSION=16 to choose; default: the newest installed)
#
# The package carries the Engine's payload (installers/payload.py, with a manifest of hashes) under /opt/falcon/payload, the command
# `falcon-engine-install`, and Falcon's own PostgreSQL under /opt/falcon/pgsql: the build server's PostgreSQL programs, copied in their own
# relative layout (installers/engine/pgsql.py). The package depends on the libraries those programs need (dpkg-shlibdeps), never on a
# postgresql package, so installing it makes or touches no cluster of the distribution's. A wheels folder makes the install work with no network.
set -eu

out="${1:-dist}"
wheels="${2:-}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"

version="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | tr -d '\r' | head -1)"   # (a checkout on Windows has CRLF lines)
pg="${PG_VERSION:-$(ls /usr/lib/postgresql 2>/dev/null | sort -n | tail -1)}"
[ -n "$pg" ] || { echo "no PostgreSQL on this build machine: install postgresql-<version> (its programs are copied into the package)" >&2; exit 1; }
arch="$(dpkg --print-architecture)"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

mkdir -p "$stage/DEBIAN" "$stage/opt/falcon" "$stage/usr/sbin"
if [ -n "$wheels" ]; then
    python3 -m installers.payload engine "$stage/opt/falcon/payload" --wheels "$wheels"
else
    python3 -m installers.payload engine "$stage/opt/falcon/payload"
fi
python3 -c "import sys; sys.path.insert(0, '.'); from pathlib import Path; from installers.engine.pgsql import assemble; \
print('PostgreSQL $pg:', assemble('$pg', Path('$stage/opt/falcon/pgsql')) >> 20, 'MB')"

# a checkout on a Windows drive (WSL's /mnt/c) reads as rwxrwxrwx: the package says exactly who may write what, whatever the checkout says
find "$stage" -type d -exec chmod 0755 {} +
find "$stage" -type f -exec chmod 0644 {} +
chmod 0755 "$stage/opt/falcon/pgsql/lib/postgresql/$pg/bin/"*

# what the PostgreSQL programs need, as the distribution's own tool says
mkdir -p "$stage/shl/debian"
printf 'Source: falcon-engine\n\nPackage: falcon-engine\nArchitecture: any\n' > "$stage/shl/debian/control"
shlibs="$(cd "$stage/shl" && dpkg-shlibdeps -O "$stage/opt/falcon/pgsql/lib/postgresql/$pg/bin/"* 2>/dev/null | sed -n 's/^shlibs:Depends=//p')"
rm -rf "$stage/shl"
[ -n "$shlibs" ] || { echo "dpkg-shlibdeps found nothing (install dpkg-dev)" >&2; exit 1; }

sed "s/@VERSION@/$version/; s/@ARCH@/$arch/; s/@SHLIBS@/$shlibs/" installers/engine/debian/control > "$stage/DEBIAN/control"
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
dpkg-deb --root-owner-group --build "$stage" "$out/falcon-engine_${version}_${arch}.deb"
echo "built $out/falcon-engine_${version}_${arch}.deb"
