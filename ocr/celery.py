import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocr_app.settings')

app = Celery('ocr_app', broker='redis://localhost:6379/0')


app.conf.enable_utc = False
app.conf.update(timezone="Asia/Kolkata")
app.conf.task_routes = {
    'ocr.tasks.re_run_ocr_for_bbox': {
        'queue': 're_run_ocr',
        'routing_key': 're_run_ocr',
        'queue_arguments': {'x-priority': 10},
    },
    'ocr.tasks.perform_ocr_for_service': {
        'queue': 'ocr_for_service',
        'routing_key': 'ocr_for_service',
        'queue_arguments': {'x-priority': 10},
    },
    'ocr.tasks.perform_ocr_for_new_upload': {
        'queue': 'new_uploads',
        'routing_key': 'new_uploads',
        'queue_arguments': {'x-priority': 5},
    },
}
app.conf.broker_transport_options = {
    'visibility_timeout': 1200,  # this doesn't affect priority, but it's part of redis config
    'queue_order_strategy': 'priority',
}

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
