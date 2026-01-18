"""Pytest configuration and fixtures."""

import pytest


# Enable asyncio for all async tests
@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    import asyncio
    return asyncio.get_event_loop_policy()
