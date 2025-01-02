import subprocess
import os

from importlib.metadata import PackageNotFoundError, version

from governanceplatform.settings import BASE_DIR


def get_version():
    """
    Returns the version of the software and the address of the exact commit
    on the project home page.
    Try to get the version from the Git tags.
    """
    version_res = ''
    if 'APP_VERSION' in os.environ:
        version_res = os.getenv('APP_VERSION')
    else:
        version_res = (
            subprocess.run(
                ["git", "-C", BASE_DIR, "describe", "--tags"], stdout=subprocess.PIPE
            )
            .stdout.decode()
            .strip()
        )

    if not version_res:
        try:
            version_res = "v" + version("governanceplatform")
        except PackageNotFoundError:
            version_res = ""

    version_parts = version_res.split("-")
    if len(version_parts) == 1:
        app_version = version_parts[0]
        version_url = "https://github.com/informed-governance-project/NISINP/releases/tag/{}".format(
            version_parts[0]
        )
    else:
        app_version = f"{version_parts[0]} - {version_parts[2][1:]}"
        version_url = (
            "https://github.com/informed-governance-project/NISINP/commits/{}".format(
                version_parts[2][1:]
            )
        )
    return {"app_version": app_version, "version_url": version_url}
