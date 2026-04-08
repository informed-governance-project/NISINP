from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from weasyprint import URLFetcher

ALLOWED_DIRS = [
    Path(settings.STATIC_ROOT).resolve(),
    Path(settings.STATIC_THEME_DIR).resolve(),
]
ALLOWED_DIRS = [d for d in ALLOWED_DIRS if d]


class RestrictedURLFetcher(URLFetcher):
    def fetch(self, url):
        parsed = urlparse(url)

        if parsed.scheme == "file":
            path = Path(parsed.path).resolve()

            for allowed_dir in ALLOWED_DIRS:
                if path.is_relative_to(allowed_dir):
                    return super().fetch(url)

        raise ValueError(f"Unsupported URL: {url}")
