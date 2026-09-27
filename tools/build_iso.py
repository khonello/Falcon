#!/usr/bin/env python3
"""
Build a disc image of the project, for moving it to another machine.

    python tools/build_iso.py                 # -> falcon-<date>.iso
    python tools/build_iso.py --with-secrets  # also .env and data/ (your own machine only)
    python tools/build_iso.py --list          # print what would go in, build nothing

What goes in is the repository — source, docs, tests, QML, `.git` — plus the
gitignored local model (`models/`, ~610 MB), which is the reason for the image:
a clone would have `python -m engine setup --download-model` fetch it again.

What stays out: the `environ-*` virtualenvs (make them fresh on the target and
`pip install -e` into them), caches and generated output, and — unless
`--with-secrets` — `.env` (database password) and `data/` (the master secret
and the TLS private key). Without them, `python -m engine setup` on the target
writes a new `.env`, a certificate for *that* machine's names, a new secret and
a first Super User, and finds the model already in place.

Backends, in the order they are tried: `xorriso`, `mkisofs`, `genisoimage`,
`hdiutil`, and on Windows the built-in IMAPI2 COM service, which needs nothing
installed. Joliet and Rock Ridge (or UDF) are requested in every case, because
plain ISO 9660 would truncate names like `hierarchy-system-design.md` to 8.3.
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VOLUME_ID = 'FALCON'

# Directories never copied, matched on the path relative to the repo root.
_EXCLUDE_DIRS = (
    'build',
    'dist',
    'logs',
    'design/boards',    # generated output (see .gitignore)
    'design/shots',
)

# Top-level virtualenvs, matched by prefix rather than by name:
# `environ-engine`, `environ-operator`, `environ-worker` today, and the next one
# is caught too.
#
# A venv is the least portable thing in the tree. Its scripts hard-code absolute
# paths to a Python that does not exist on the target machine, and its compiled
# extensions are built for one interpreter version and architecture, so carrying
# one is worse than useless — it looks like a working environment and is not.
_EXCLUDE_DIR_PREFIX = 'environ'

# Directory *names* skipped wherever they appear, and name suffixes likewise.
_EXCLUDE_NAMES = ('__pycache__', '.mypy_cache', '.pytest_cache', '.ruff_cache')
_EXCLUDE_SUFFIXES = ('.egg-info',)

# Files never copied unless `--with-secrets`.
#
# `.env*` is matched as a *prefix*, so a `.env.backup-...` copy is held back
# too; `.env.example` is the documented template and carries no values.
# `data/` is the Engine's host state: `master.secret` (every client key derives
# from it) and `engine.key` (the TLS private key).
_SECRET_PREFIX = '.env'
_SECRET_ALLOWED = ('.env.example',)
_SECRET_DIRS = ('data',)


def _is_secret(rel: str) -> bool:
    """Whether a repo-relative path holds credentials and needs `--with-secrets`."""
    name = rel.rsplit('/', 1)[-1]
    if name.startswith(_SECRET_PREFIX) and name not in _SECRET_ALLOWED:
        return True
    return rel.split('/', 1)[0] in _SECRET_DIRS


def _rel(path: str) -> str:
    return os.path.relpath(path, _REPO_ROOT).replace('\\', '/')


def _included(with_secrets: bool) -> tuple[list[str], int]:
    """
    Every file that belongs in the image, and their total size.

    Returns:
        (relative paths, total bytes)
    """
    keep: list[str] = []
    total = 0

    for dirpath, dirnames, filenames in os.walk(_REPO_ROOT):
        rel_dir = _rel(dirpath)
        if rel_dir == '.':
            rel_dir = ''

        # Prune in place so os.walk does not descend into them at all — the
        # excluded trees are most of the bytes, and walking them is most of the
        # time this would otherwise take.
        dirnames[:] = [
            d for d in dirnames
            if d not in _EXCLUDE_NAMES
            and not d.endswith(_EXCLUDE_SUFFIXES)
            and (f'{rel_dir}/{d}'.lstrip('/') not in _EXCLUDE_DIRS)
            and not (rel_dir == '' and d.startswith(_EXCLUDE_DIR_PREFIX))
        ]

        for name in filenames:
            rel = f'{rel_dir}/{name}'.lstrip('/')
            if name.endswith('.iso'):
                continue
            if _is_secret(rel) and not with_secrets:
                continue
            full = os.path.join(dirpath, name)
            try:
                total += os.path.getsize(full)
            except OSError:
                continue
            keep.append(rel)

    return (sorted(keep), total)


def _stage(paths: list[str], staging: str) -> None:
    """Copy the included files into a clean tree the backend can read."""
    for i, rel in enumerate(paths, 1):
        dest = os.path.join(staging, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(os.path.join(_REPO_ROOT, rel), dest)
        if i % 500 == 0:
            print(f'  staged {i} / {len(paths)} files')


# ── Backends ───────────────────────────────────────────────────────────


def _unix_backend() -> list[str] | None:
    """The first available command-line ISO writer, as an argv template."""
    for name in ('xorriso', 'mkisofs', 'genisoimage'):
        if shutil.which(name):
            if name == 'xorriso':
                return [name, '-as', 'mkisofs', '-J', '-r', '-V', _VOLUME_ID,
                        '-o', '{iso}', '{dir}']
            return [name, '-J', '-r', '-V', _VOLUME_ID, '-o', '{iso}', '{dir}']
    if shutil.which('hdiutil'):
        return ['hdiutil', 'makehybrid', '-iso', '-joliet',
                '-default-volume-name', _VOLUME_ID, '-o', '{iso}', '{dir}']
    return None


# IMAPI2 is the service Windows itself uses to burn discs, so it is present on
# every Windows 10/11 machine and needs no install. Writing the resulting
# IStream to a file is the one part with no PowerShell equivalent, hence the
# small inline C#.
_IMAPI_PS = r'''
$ErrorActionPreference = 'Stop'
$stage = $args[0]
$iso   = $args[1]
$label = $args[2]

Add-Type -TypeDefinition @"
using System;
using System.IO;
using System.Runtime.InteropServices.ComTypes;
public static class IsoWriter {
    [System.Runtime.InteropServices.DllImport("shlwapi.dll", CharSet =
        System.Runtime.InteropServices.CharSet.Unicode,
        ExactSpelling = true, PreserveSig = false)]
    private static extern void SHCreateStreamOnFileEx(
        string f, uint m, uint d, bool c, IStream r, out IStream s);
    public static void Write(object stream, string path) {
        IStream inStream = (IStream)stream;
        IStream outStream;
        SHCreateStreamOnFileEx(path, 0x1001, 0x80, true, null, out outStream);
        try { inStream.CopyTo(outStream, Int64.MaxValue, IntPtr.Zero,
                              IntPtr.Zero); outStream.Commit(0); }
        finally {
            System.Runtime.InteropServices.Marshal.ReleaseComObject(outStream);
        }
    }
}
"@

$fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
# ISO9660 | Joliet | UDF. Joliet and UDF are what carry long names; ISO9660
# alone would truncate to 8.3.
$fsi.FileSystemsToCreate = 7
# The default capacity is a CD's, and the model alone nearly fills one.
# 0 lifts the limit.
$fsi.FreeMediaBlocks = 0
$fsi.VolumeName = $label
$fsi.Root.AddTree($stage, $false)
$result = $fsi.CreateResultImage()
[IsoWriter]::Write($result.ImageStream, $iso)
'''


def _build_windows(staging: str, iso: str) -> int:
    script = os.path.join(tempfile.gettempdir(), 'falcon_mkiso.ps1')
    with open(script, 'w', encoding='utf-8') as fh:
        fh.write(_IMAPI_PS)
    try:
        return subprocess.call([
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', script, staging, iso, _VOLUME_ID,
        ])
    finally:
        try:
            os.remove(script)
        except OSError:
            pass


def build(staging: str, iso: str) -> int:
    template = _unix_backend()
    if template is not None:
        cmd = [a.replace('{iso}', iso).replace('{dir}', staging)
               for a in template]
        print('  $ {}'.format(' '.join(cmd)))
        return subprocess.call(cmd)

    if sys.platform == 'win32':
        print('  using the built-in IMAPI2 service')
        return _build_windows(staging, iso)

    print('No ISO writer found. Install xorriso, mkisofs or genisoimage.')
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Build a disc image of the project.')
    parser.add_argument('--output', help='output path (default falcon-<date>.iso)')
    parser.add_argument('--with-secrets', action='store_true',
                        help='include .env and data/ (database password, master '
                             'secret, TLS key) -- for your own machine only')
    parser.add_argument('--list', action='store_true',
                        help='print what would be included, build nothing')
    args = parser.parse_args(argv)

    paths, total = _included(args.with_secrets)
    mb = total / (1024.0 * 1024.0)

    if args.list:
        for rel in paths:
            print(rel)
        print(f'\n{len(paths)} files, {mb:.1f} MB')
        return 0

    iso = args.output or 'falcon-{}.iso'.format(
        datetime.datetime.now().astimezone().strftime('%Y%m%d'))
    iso = os.path.abspath(iso)

    print(f'Falcon -> {iso}')
    print(f'  {len(paths)} files, {mb:.1f} MB')
    if args.with_secrets:
        secrets = [p for p in paths if _is_secret(p)]
        print('  WARNING: this image carries credentials - do not hand it to '
              'anyone else:')
        for rel in secrets:
            print(f'           {rel}')
    else:
        print('  .env and data/ excluded (pass --with-secrets if this image is '
              'for your own machine)')
    if not any(p.startswith('models/') for p in paths):
        print('  WARNING: no models/ -- the target will need '
              '`python -m engine setup --download-model`')

    staging = tempfile.mkdtemp(prefix='falcon-iso-')
    try:
        print('\nStaging...')
        _stage(paths, staging)
        print('\nBuilding...')
        status = build(staging, iso)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    if status != 0:
        print('\nFailed.')
        return status

    if not os.path.isfile(iso):
        print('\nThe backend reported success but wrote no file.')
        return 1

    print(f'\nWrote {iso} ({os.path.getsize(iso) / (1024.0 * 1024.0):.1f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
