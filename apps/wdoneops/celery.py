from __future__ import absolute_import, unicode_literals
import os
import datetime
from celery import Celery, platforms

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wdoneops.settings')

celery_app = Celery('wdoneops')
celery_app.now = datetime.datetime.now

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
celery_app.autodiscover_tasks()

platforms.C_FORCE_ROOT = True


@celery_app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
