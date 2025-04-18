from governanceplatform import tools
from .celery import app as celery_app

__version__ = tools.get_version()
__all__ = ['celery_app']
