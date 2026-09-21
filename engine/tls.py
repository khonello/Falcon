"""Self-signed Engine certificate (spec 8.3): one Engine, every client receives the certificate in
its install package and pins it (`--ca`). Identity is hostname-based, so the certificate carries
the names clients will use (DNS names and/or IP literals) as Subject Alternative Names.

    python -m engine gencert engine.corp.local,10.0.0.5 [out_dir]
"""

from __future__ import annotations

import datetime as dt
import ipaddress
from pathlib import Path

VALID_DAYS = 3650


def generate_self_signed(names: str, out_dir: Path, *, valid_days: int = VALID_DAYS) -> tuple[Path, Path]:
    """Write `<out_dir>/engine.crt` + `engine.key` for the comma-separated names; returns their paths."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    labels = [n.strip() for n in names.split(",") if n.strip()]
    if not labels:
        raise ValueError("at least one hostname or IP is required")
    sans: list[x509.GeneralName] = []
    for label in labels:
        try:
            sans.append(x509.IPAddress(ipaddress.ip_address(label)))
        except ValueError:
            sans.append(x509.DNSName(label))

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, labels[0]),
                         x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Falcon Engine")])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(minutes=5))
            .not_valid_after(now + dt.timedelta(days=valid_days))
            .add_extension(x509.SubjectAlternativeName(sans), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256()))

    out_dir.mkdir(parents=True, exist_ok=True)
    cert_path, key_path = out_dir / "engine.crt", out_dir / "engine.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    return cert_path, key_path
