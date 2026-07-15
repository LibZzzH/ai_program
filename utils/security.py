import hashlib
import hmac
import os


PBKDF2_ITERATIONS = 200_000
PBKDF2_ALGORITHM = "sha256"


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash or "$" not in password_hash:
        return False

    if password_hash.startswith("pbkdf2_"):
        try:
            algorithm_tag, iterations, salt, expected = password_hash.split("$", 3)
            algorithm = algorithm_tag.removeprefix("pbkdf2_")
            digest = hashlib.pbkdf2_hmac(
                algorithm,
                password.encode("utf-8"),
                bytes.fromhex(salt),
                int(iterations),
            ).hex()
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(expected, digest)

    salt, h = password_hash.split("$", 1)
    legacy_digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return hmac.compare_digest(h, legacy_digest)
