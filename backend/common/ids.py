"""Entity identifiers, ported from the original IdGenerator."""

import hashlib
import uuid


def generate(prefix):
    to_hash = f"{prefix}-{uuid.uuid4()}"
    return f"{prefix}-{hashlib.sha256(to_hash.encode('utf-8')).hexdigest()[:20].upper()}"
