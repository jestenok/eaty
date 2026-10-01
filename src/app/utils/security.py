"""Passwords and sign-in tokens, with the standard library only."""

from __future__ import annotations

import functools
import hashlib
import hmac
import secrets

# scrypt cost: ~16 MB and a few dozen ms per hash. Stored with the hash, so it can be raised later.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Whether the password matches the stored hash. Without a hash (no such user) it still
    spends the time of a check, so the answer's speed doesn't tell which logins exist."""
    if stored is None:
        _matches(password, _decoy_hash())
        return False
    return _matches(password, stored)


def _matches(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(digest)
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                                dklen=len(expected))
    except ValueError:  # '' of the account nobody has signed up for yet, or a damaged hash
        return False
    return hmac.compare_digest(actual, expected)


@functools.cache
def _decoy_hash() -> str:
    return hash_password(secrets.token_hex(16))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
