"""Utilities for Python HomeWizard Energy."""

from functools import lru_cache

from awesomeversion import AwesomeVersion


@lru_cache
def get_awesome_version(version: str) -> AwesomeVersion:
    """Return a cached AwesomeVersion object."""
    if version.lower() == "v1":
        return AwesomeVersion("1.0.0")
    return AwesomeVersion(version)
