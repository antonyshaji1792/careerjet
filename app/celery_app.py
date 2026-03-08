from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

def make_celery(app_name=None):
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    celery = Celery(
        app_name or 'careerjet',
        backend=redis_url,
        broker=redis_url
    )
    
    # Configure periodic tasks
    celery.conf.beat_schedule = {
        'run-autopilot-every-hour': {
            'task': 'app.tasks.celery_tasks.run_all_autopilots_task',
            'schedule': 3600.0, # Every hour
        },
    }
    celery.conf.timezone = 'UTC'
    
    return celery

celery = make_celery()
