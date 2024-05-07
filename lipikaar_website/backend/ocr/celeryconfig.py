task_routes = {
    'tasks.perform_ocr_for_new_upload': {'queue': 'new_upload'},
    'tasks.re_run_ocr_for_bbox': {'queue': 're_run_ocr'},
}

task_queues = {
    'new_upload': {
        'exchange': 'new_upload',
        'routing_key': 'new_upload',
    },
    're_run_ocr': {
        'exchange': 're_run_ocr',
        'routing_key': 're_run_ocr',
    },
}

task_default_queue = 'new_upload'