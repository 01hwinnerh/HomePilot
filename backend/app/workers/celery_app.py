from celery import Celery

from app.core.config import get_settings

celery_app = Celery("homepilot", broker=get_settings().redis_url)
