import os
from celery import Celery
from autorubric.core.config import config

REDIS_URL = config.REDIS_URL

celery_app = Celery(
    "autorubric_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["autorubric.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "autorubric.workers.tasks.evaluate_task": {"queue": "gpu_queue"},
        "autorubric.workers.tasks.*": {"queue": "celery"},
    }
)

if REDIS_URL.startswith("rediss://"):
    import ssl
    celery_app.conf.update(
        broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
        redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
    )
