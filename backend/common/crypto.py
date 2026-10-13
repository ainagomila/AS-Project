"""Reversible field encryption, ported from the original EncryptionService.

AES-256-GCM, 12-byte random IV, 16-byte tag. IV, ciphertext and tag are stored
separately as base64 strings.
"""

import base64
import json
import os
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

IV_LENGTH_BYTES = 12
TAG_LENGTH_BYTES = 16


@lru_cache(maxsize=1)
def _key():
    key_b64 = None
    key_file = Path(settings.SECURITY_ENCRYPTION_KEY_FILE or "")
    if settings.SECURITY_ENCRYPTION_KEY_FILE and key_file.exists():
        try:
            key_b64 = json.loads(key_file.read_text(encoding="utf-8"))["keyBase64"]
        except (OSError, ValueError, KeyError):
            key_b64 = None
    if not key_b64 and settings.SECURITY_ENCRYPTION_KEY_BASE64:
        key_b64 = settings.SECURITY_ENCRYPTION_KEY_BASE64
    if not key_b64:
        raise RuntimeError(
            "No s'ha pogut obtenir la clau d'encriptació! Configura "
            "SECURITY_ENCRYPTION_KEY_FILE o SECURITY_ENCRYPTION_KEY_BASE64"
        )
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise ValueError("La clau ha de tenir 32 bytes!")
    return key


def encrypt(plain_text):
    """Return (iv, ciphertext, tag), each base64-encoded."""
    iv = os.urandom(IV_LENGTH_BYTES)
    cipher_with_tag = AESGCM(_key()).encrypt(iv, plain_text.encode("utf-8"), None)
    cipher, tag = cipher_with_tag[:-TAG_LENGTH_BYTES], cipher_with_tag[-TAG_LENGTH_BYTES:]
    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    return b64(iv), b64(cipher), b64(tag)


def decrypt(iv, ciphertext, tag):
    cipher_with_tag = base64.b64decode(ciphertext) + base64.b64decode(tag)
    plain = AESGCM(_key()).decrypt(base64.b64decode(iv), cipher_with_tag, None)
    return plain.decode("utf-8")
