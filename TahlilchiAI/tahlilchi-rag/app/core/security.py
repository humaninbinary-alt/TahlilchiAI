"""Security utilities for password hashing and validation."""

import logging
import re
from typing import Tuple

from passlib.hash import bcrypt, pbkdf2_sha256

logger = logging.getLogger(__name__)
_bcrypt_available = True


def _hash_with_bcrypt(password: str) -> str:
    """Attempt to hash using bcrypt (preferred)."""
    global _bcrypt_available
    if not _bcrypt_available:
        raise RuntimeError("bcrypt backend disabled")
    return bcrypt.using(rounds=12).hash(password)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with automatic fallback to PBKDF2-SHA256.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    global _bcrypt_available
    try:
        return _hash_with_bcrypt(password)
    except Exception:
        if _bcrypt_available:
            logger.warning(
                "bcrypt backend unavailable; falling back to PBKDF2-SHA256. "
                "Install the 'bcrypt' extra for production-grade hashing."
            )
        _bcrypt_available = False
        return pbkdf2_sha256.using(rounds=480_000).hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    if _bcrypt_available:
        try:
            return bcrypt.verify(plain_password, hashed_password)
        except Exception:
            pass
    return pbkdf2_sha256.verify(plain_password, hashed_password)


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.

    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"

    return True, ""
