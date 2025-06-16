import os
import subprocess
from importlib.metadata import PackageNotFoundError, version

from governanceplatform.settings import BASE_DIR


def get_version():
    """
    Returns a dictionary containing:
    - The app version (from environment or Git tag),
    - The version URL on GitHub,
    - The version from pyproject.toml (or fallback).
    """

    # Get version from pyproject.toml
    try:
        app_version_from_pyproject = version("governanceplatform")
    except PackageNotFoundError:
        app_version_from_pyproject = "inconnue"

    # Try to get version from env or Git tags
    app_version = os.environ.get("APP_VERSION")

    if not app_version:
        try:
            result = subprocess.run(
                ["git", "-C", BASE_DIR, "describe", "--tags"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            app_version = result.stdout.decode().strip()
        except subprocess.SubprocessError:
            app_version = ""

    # Final fallback to pyproject version if Git version is unavailable
    if not app_version:
        app_version = f"v{app_version_from_pyproject}"

    version_url = f"https://github.com/informed-governance-project/NISINP/releases/tag/{app_version}"

    return {
        "app_version": app_version,
        "version_url": version_url,
        "app_version_from_pyproject": app_version_from_pyproject,
    }
