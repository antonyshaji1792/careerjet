from app import create_app
from app.celery_app import celery
from app.tasks import celery_tasks # Ensure tasks are registered

app = create_app()
app.app_context().push()
