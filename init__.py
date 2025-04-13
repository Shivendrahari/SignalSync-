# myproject/__init__.py
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # For development, allow the server to start even if Celery isn't set up yet
    pass