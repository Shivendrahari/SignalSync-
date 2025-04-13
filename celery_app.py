# myproject/celery.py
from __future__ import absolute_import
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    
app.conf.beat_schedule = {
    'poll-devices-every-5-minutes': {
        'task': 'network.tasks.poll_all_devices',
        'schedule': 300.0,  # 5 minutes in seconds
    },
    'cleanup-old-stats-daily': {
        'task': 'network.tasks.cleanup_old_stats',
        'schedule': 86400.0,  # 24 hours in seconds
    },
}