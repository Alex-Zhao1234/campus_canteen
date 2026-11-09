"""APScheduler 封装：只负责"什么时候跑"，任务本身在 app/tasks/。"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.tasks.rankings import rebuild_rankings

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def rebuild_rankings_job() -> None:
    async with SessionLocal() as session:
        summary = await rebuild_rankings(session)
    log.info("榜单任务完成：%s", summary)


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled:
        log.info("调度器已禁用（SCHEDULER_ENABLED=false）")
        return
    scheduler.add_job(
        rebuild_rankings_job,
        "interval",
        minutes=settings.ranking_interval_minutes,
        id="rebuild_rankings",
        next_run_time=datetime.now(),  # 启动即跑一次，首页一开始就有榜单
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    log.info("调度器已启动：榜单每 %d 分钟重算", settings.ranking_interval_minutes)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
