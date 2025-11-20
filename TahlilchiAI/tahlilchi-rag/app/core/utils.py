"""Core utility functions."""

import re
import unicodedata


def generate_slug(name: str) -> str:
    """
    Generate URL-safe slug from chat name.

    Example:
        "HR Policy Assistant" → "hr-policy-assistant"
        "Политика HR" → "politika-hr"

    Args:
        name: The original name to convert

    Returns:
        str: URL-safe slug
    """
    # Normalize unicode characters
    name = unicodedata.normalize("NFKD", name)

    # Convert to lowercase
    name = name.lower()

    # Replace spaces and underscores with hyphens
    name = re.sub(r"[\s_]+", "-", name)

    # Remove any character that's not alphanumeric or hyphen
    name = re.sub(r"[^a-z0-9\-]", "", name)

    # Remove multiple consecutive hyphens
    name = re.sub(r"-+", "-", name)

    # Strip hyphens from start and end
    name = name.strip("-")

    return name or "chat"
