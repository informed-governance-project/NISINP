import os
from importlib.metadata import PackageNotFoundError, version


def get_version():
    """
    Returns a dictionary containing:
    - The app version (from environment variable or fallback to pyproject.toml),
    - The version URL on GitHub,
    - The version from pyproject.toml (or fallback).
    """

    # Get version from pyproject.toml
    try:
        app_version_from_pyproject = version("governanceplatform")
    except PackageNotFoundError:
        app_version_from_pyproject = "unknown"

    # Try to get version from env
    app_version = os.environ.get("APP_VERSION")

    # Final fallback to pyproject version if Git version is unavailable
    if not app_version:
        app_version = f"v{app_version_from_pyproject}"

    return {
        "app_version": app_version,
        "app_version_from_pyproject": app_version_from_pyproject,
    }
