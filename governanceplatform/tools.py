import os
import subprocess

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_version():
    """
    Returns the version of the software and the address of the exact commit
    on the project home page.
    Try to get the version from the Git tags.
    """
    version_res = (
        subprocess.run(
            ["git", "-C", BASE_DIR, "describe", "--tags"], stdout=subprocess.PIPE
        )
        .stdout.decode()
        .strip()
    ) or ""
    version = version_res.split("-")
    if len(version) == 1:
        app_version = version[0]
        version_url = "https://github.com/informed-governance-project/governance-platform/releases/tag/{}".format(
            version[0]
        )
    else:
        app_version = f"{version[0]} - {version[2][1:]}"
        version_url = "https://github.com/informed-governance-project/governance-platform/commits/{}".format(
            version[2][1:]
        )
    return {"app_version": app_version, "version_url": version_url}
