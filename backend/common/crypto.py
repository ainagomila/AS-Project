"""Field encryption and blind indexes.

Values are AES-256-GCM encrypted as "v1:<key id>:<nonce>:<ciphertext+tag>", with
"<table>.<column>.<row id>" as associated data, so a value only decrypts in its own
cell. Lookups use an HMAC-SHA256 blind index under a separate key.

Keyring file: {"current": "k2", "keys": {"k1": b64, "k2": b64}, "indexKeyBase64": b64}.
The older {"keyBase64": b64} file (or SECURITY_ENCRYPTION_KEY_BASE64) is read as
key "k1", with the index key derived from it.
"""

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

VERSION = "v1"
NONCE_BYTES = 12


@dataclass(frozen=True)
class Keyring:
    current: str
    keys: dict
    index_key: bytes


def _b64(data):
    return base64.b64encode(data).decode("ascii")


def _key_bytes(b64):
    key = base64.b64decode(b64)
    if len(key) != 32:
        raise ValueError("La clau ha de tenir 32 bytes!")
    return key


def derive_index_key(key):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"kofre blind index").derive(key)


def read_keyring_file(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def parse_keyring(data):
    if "keyBase64" in data:  # single-key format from before the keyring
        data = {"current": "k1", "keys": {"k1": data["keyBase64"]}}
    keys = {kid: _key_bytes(b64) for kid, b64 in data["keys"].items()}
    if "indexKeyBase64" in data:
        index_key = _key_bytes(data["indexKeyBase64"])
    else:
        index_key = derive_index_key(keys["k1"])
    return Keyring(data["current"], keys, index_key)


@lru_cache(maxsize=1)
def _keyring():
    path = settings.SECURITY_ENCRYPTION_KEY_FILE
    data = read_keyring_file(path) if path else None
    if not data and settings.SECURITY_ENCRYPTION_KEY_BASE64:
        data = {"keyBase64": settings.SECURITY_ENCRYPTION_KEY_BASE64}
    if not data:
        raise RuntimeError(
            "No s'ha pogut obtenir la clau d'encriptació! Configura "
            "SECURITY_ENCRYPTION_KEY_FILE o SECURITY_ENCRYPTION_KEY_BASE64"
        )
    return parse_keyring(data)


def context(table, column, row_id):
    if not row_id:
        raise ValueError("The row id must be set before encrypting a field")
    return f"{table}.{column}.{row_id}"


def encrypt(plain, aad):
    ring = _keyring()
    nonce = os.urandom(NONCE_BYTES)
    cipher = AESGCM(ring.keys[ring.current]).encrypt(nonce, plain.encode("utf-8"), aad.encode())
    return f"{VERSION}:{ring.current}:{_b64(nonce)}:{_b64(cipher)}"


def decrypt(token, aad):
    version, kid, nonce, cipher = token.split(":")
    if version != VERSION:
        raise ValueError(f"Unknown ciphertext version {version}")
    key = _keyring().keys[kid]
    plain = AESGCM(key).decrypt(base64.b64decode(nonce), base64.b64decode(cipher), aad.encode())
    return plain.decode("utf-8")


def decrypt_legacy(iv, ciphertext, tag):
    """Values written before v1: key k1, separate IV/ciphertext/tag, no associated data."""
    cipher_with_tag = base64.b64decode(ciphertext) + base64.b64decode(tag)
    plain = AESGCM(_keyring().keys["k1"]).decrypt(base64.b64decode(iv), cipher_with_tag, None)
    return plain.decode("utf-8")


def blind_index(value, purpose):
    message = f"{purpose}:{value}".encode("utf-8")
    return hmac.new(_keyring().index_key, message, hashlib.sha256).hexdigest()


def encrypted(column, normalize=None, index=None):
    """Model property stored encrypted in `column` and bound to the row id.

    `index` is (index column, function giving the blind index of a value).
    """

    def aad(obj):
        return context(obj._meta.db_table, column, obj.pk)

    def fget(obj):
        token = getattr(obj, column)
        return decrypt(token, aad(obj)) if token else None

    def fset(obj, value):
        if normalize:
            value = normalize(value)
        setattr(obj, column, encrypt(value, aad(obj)))
        if index:
            setattr(obj, index[0], index[1](value))

    return property(fget, fset)
