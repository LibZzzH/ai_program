import hashlib

from utils.security import hash_password, verify_password


def test_hash_password_uses_pbkdf2_and_verifies():
    password_hash = hash_password("abc123")

    assert password_hash.startswith("pbkdf2_sha256$")
    assert verify_password("abc123", password_hash)
    assert not verify_password("wrong", password_hash)


def test_verify_password_keeps_legacy_sha256_hashes_working():
    salt = "00" * 16
    legacy_hash = hashlib.sha256((salt + "abc123").encode()).hexdigest()

    assert verify_password("abc123", f"{salt}${legacy_hash}")
    assert not verify_password("wrong", f"{salt}${legacy_hash}")
