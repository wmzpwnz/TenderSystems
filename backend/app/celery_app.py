"""
Конфигурация Celery для фоновых задач
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "tender_hacker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.analysis_tasks", "app.tasks.sync_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 минут
    task_soft_time_limit=240,  # 4 минуты
)

# Настройка Celery Beat для периодических задач
celery_app.conf.beat_schedule = {
    # Синхронизация новых тендеров каждый час
    'sync-new-tenders-hourly': {
        'task': 'sync_new_tenders',
        'schedule': crontab(minute='*/30'),  # Каждые 30 минут
        'kwargs': {'limit': 100}
    },

    # Обновление неполных тендеров каждые 6 часов
    'refresh-incomplete-tenders': {
        'task': 'refresh_incomplete_tenders',
        'schedule': crontab(minute=0, hour='*/6'),  # Каждые 6 часов
        'kwargs': {'limit': 50}
    },

    # Очистка старых тендеров раз в день
    'cleanup-old-tenders-daily': {
        'task': 'cleanup_old_tenders',
        'schedule': crontab(minute=0, hour=3),  # Каждый день в 3:00 UTC
        'kwargs': {'days': 180}
    },
}















