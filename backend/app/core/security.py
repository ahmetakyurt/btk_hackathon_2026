from __future__ import annotations

import secrets

import bcrypt

# bcrypt has a 72-byte limit on the input password. We truncate silently to
# match common practice (NIST SP 800-63B allows it). Users typing >72-char
# passwords still authenticate consistently.
_BCRYPT_MAX_BYTES = 72


def _to_bytes(plain: str) -> bytes:
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_to_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)
