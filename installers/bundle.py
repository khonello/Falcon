"""The client bundle: what every Windows installer is given about the Engine, and nothing more.

    {"engine_host": "falcon.internal", "engine_port": 7400, "ca_pem": "-----BEGIN CERTIFICATE-----...", "ca_sha256": "AB:CD:..."}

The Engine's installer writes it (`falcon-client.json`); the same file goes to every machine. It holds the Engine's address and its
certificate, so a machine reaches the real Engine on its first connection and no other. It holds NO key and NO client id: a machine is
given its own by being registered (it asks, and an Admin or the Super User confirms), and the Super User's is typed once.

`ca_sha256` is the certificate's fingerprint. The person installing can compare it with the one the Engine's installer printed, read out
or sent another way, to be sure the bundle itself was not swapped on its way: pass `--fingerprint` to an installer and it refuses a mismatch.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from installers.common import InstallError, cert_fingerprint


@dataclass
class Bundle:
    engine_host: str
    engine_port: int
    ca_pem: str
    ca_sha256: str

    @classmethod
    def make(cls, host: str, port: int, cert_pem: str) -> Bundle:
        return cls(host, int(port), cert_pem.strip() + "\n", cert_fingerprint(cert_pem))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def load(path: Path, fingerprint: str | None = None) -> Bundle:
    """Read a bundle and check it is whole; with `fingerprint`, that it holds the certificate the person expects."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        bundle = Bundle(str(data["engine_host"]), int(data["engine_port"]), str(data["ca_pem"]), str(data["ca_sha256"]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise InstallError(f"{path} is not a Falcon client bundle ({exc})") from exc
    if not bundle.engine_host or not (0 < bundle.engine_port < 65536):
        raise InstallError(f"{path} does not say where the Engine is")
    try:
        actual = cert_fingerprint(bundle.ca_pem)
    except ValueError as exc:
        raise InstallError(f"the certificate in {path} is not a certificate") from exc
    if actual != bundle.ca_sha256:
        raise InstallError("the certificate in the bundle does not match the fingerprint written beside it: the file was changed")
    if fingerprint and _plain(fingerprint) != _plain(actual):
        raise InstallError(f"the bundle's certificate is {actual}, not {fingerprint}: this is not the Engine you expected")
    return bundle


def _plain(fp: str) -> str:
    return "".join(ch for ch in fp.upper() if ch in "0123456789ABCDEF")
