from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from weasyprint import default_url_fetcher

ALLOWED_DIRS = [
    Path(settings.STATIC_ROOT).resolve(),
    Path(settings.STATIC_THEME_DIR).resolve(),
]
ALLOWED_DIRS = [d for d in ALLOWED_DIRS if d]


def restricted_url_fetcher(url):
    parsed = urlparse(url)
    # only local file
    if parsed.scheme == "file":
        path = Path(parsed.path).resolve()

        for allowed_dir in ALLOWED_DIRS:
            if path.is_relative_to(allowed_dir):
                return default_url_fetcher(url)

    raise ValueError(f"Unsupported URL scheme: {url}")
