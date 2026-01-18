"""Helper utility functions."""

import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    unique_id = uuid.uuid4().hex[:8]
    if prefix:
        return f"{prefix}-{unique_id}"
    return unique_id
