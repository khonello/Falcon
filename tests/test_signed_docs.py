"""Ed25519 in the standard library (common/ed25519.py) and the store's signed documents (common/signed.py): docs/STORE-CONTRACT.md section 2.
A signature Falcon accepts must be exactly the store's, over exactly the document; anything else is refused, with no internet."""

from __future__ import annotations

import base64

import pytest

from common import ed25519, signed, store_keys

# RFC 8032, section 7.1, tests 1-3: (public key, message, signature)
RFC8032 = [
    ("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025", "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]


def _signer():
    pytest.importorskip("cryptography")                                     # only the stand-in store signs; Falcon itself only verifies
    from scripts.store_stub import sign

    return sign


@pytest.mark.parametrize(("pub", "msg", "sig"), RFC8032)
def test_the_rfc_8032_vectors_verify_and_any_change_does_not(pub, msg, sig):
    p, m, s = bytes.fromhex(pub), bytes.fromhex(msg), bytes.fromhex(sig)
    assert ed25519.verify(p, m, s)
    assert not ed25519.verify(p, m + b"x", s)
    assert not ed25519.verify(p, m, s[:-1] + bytes([s[-1] ^ 1]))
    assert not ed25519.verify(bytes(32), m, s) and not ed25519.verify(p, m, s[:63])


def test_a_malleable_signature_is_refused():
    pub, msg, sig = (bytes.fromhex(x) for x in RFC8032[0])
    s = int.from_bytes(sig[32:], "little") + ed25519.L                 # the same point, another s: RFC 8032 requires s < L
    assert not ed25519.verify(pub, msg, sig[:32] + s.to_bytes(32, "little"))


def test_the_signed_bytes_are_sorted_compact_json_and_refuse_fractions():
    assert signed.canonical({"b": 1, "a": "é", "c": [2, {"z": 1, "y": 2}]}) == '{"a":"é","b":1,"c":[2,{"y":2,"z":1}]}'.encode()
    with pytest.raises(signed.SignatureError, match="fraction"):
        signed.canonical({"seats": 1.5})


def test_a_store_document_is_accepted_only_whole_of_its_kind_and_by_a_trusted_key(monkeypatch):
    sign = _signer()
    doc = {"kind": "grant", "grant_id": "g_1", "company_id": "c_1", "engine_id": "e_1", "role": "worker", "seats": 20,
           "valid_from": "2026-11-14T00:00:00Z", "valid_until": "2027-11-14T00:00:00Z", "paddle_ref": "sub_1", "issued_at": "2026-11-14T00:00:00Z"}
    env = sign(doc)
    monkeypatch.delenv("FALCON_STORE_TEST_KEY", raising=False)
    with pytest.raises(signed.SignatureError, match="does not know"):
        signed.check(env, "grant")                                    # the test key is never trusted by default
    monkeypatch.setenv("FALCON_STORE_TEST_KEY", "1")
    assert signed.check(env, "grant") == doc
    with pytest.raises(signed.SignatureError, match="not a 'company'"):
        signed.check(env, "company")
    changed = {**env, "doc": {**doc, "seats": 200}}
    with pytest.raises(signed.SignatureError, match="does not match"):
        signed.check(changed, "grant")
    with pytest.raises(signed.SignatureError, match="not readable"):
        signed.check({**env, "sig": "***"}, "grant")
    other = {"other-1": bytes.fromhex(RFC8032[0][0])}
    with pytest.raises(signed.SignatureError, match="does not know"):
        signed.check(env, "grant", keys=other)
    assert store_keys.TEST_KID in store_keys.trusted() and not store_keys.STORE_KEYS.get(store_keys.TEST_KID)


def test_a_company_file_is_read_from_disk_and_refused_once_edited(tmp_path, monkeypatch):
    sign = _signer()
    import json

    monkeypatch.setenv("FALCON_STORE_TEST_KEY", "1")
    env = sign({"kind": "company", "company_id": "c_1", "company_name": "Acme", "engine_id": "e_1", "names": ["falcon.internal"], "port": 7400,
                "certificates": ["-----BEGIN CERTIFICATE-----x"], "issued_at": "2026-11-14T00:00:00Z"})
    f = tmp_path / "acme.falcon"
    f.write_text(json.dumps(env), encoding="utf-8")
    assert signed.load(f, "company")["names"] == ["falcon.internal"]
    env["doc"]["names"] = ["rogue.example"]                             # pointed at another Engine
    f.write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(signed.SignatureError):
        signed.load(f, "company")
    assert base64.b64decode(env["sig"])                                 # (the signature itself was left alone)
