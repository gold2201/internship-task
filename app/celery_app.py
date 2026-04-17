from celery import Celery

celery_app = Celery(
    "app",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_ignore_result=False,
    result_expires=300,
)

celery_app.autodiscover_tasks(["app.celery_tasks.celery_analytics_tasks.tasks"])
