from celery import Celery
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

celery_app = Celery("worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)


celery_app.conf.worker_hijack_root_logger = False
celery_app.conf.imports = ("app.workers.tasks",)
celery_app.conf.beat_schedule = {
    "cleanup-expired-uploads": {
        "task": "app.workers.tasks.cleanup_expired_uploads",
        "schedule": settings.CLEANUP_INTERVAL_SECONDS,
    }
}
