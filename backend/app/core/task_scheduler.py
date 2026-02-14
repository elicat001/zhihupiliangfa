"""
任务调度器
使用 APScheduler 管理定时发布任务、批量发文队列、失败重试
支持指数退避重试、发布时间随机抖动（反检测）、SSE 实时事件推送
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update, func

from app.config import settings
from app.database.connection import async_session_factory
from app.models.article import Article
from app.models.account import Account
from app.models.task import PublishTask, PublishRecord
from app.models.log import SystemLog
from app.core.zhihu_publisher import zhihu_publisher
from app.api.events import event_bus
from app.automation.anti_detect import get_random_jitter_minutes

logger = logging.getLogger(__name__)

# ==================== 指数退避重试常量 ====================
RETRY_BASE_DELAY_SECONDS = 60       # 基础延迟 60 秒
RETRY_MAX_DELAY_SECONDS = 30 * 60   # 最大延迟 30 分钟
RETRY_JITTER_MAX_SECONDS = 30       # 随机抖动上限 30 秒


class TaskScheduler:
    """
    发布任务调度器
    - 管理定时任务
    - 频率控制（每日上限、最小间隔、活跃时间窗口）
    - 批量发文队列处理
    - 失败自动重试
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self._running = False

    def start(self):
        """启动调度器"""
        if self._running:
            return

        # 添加定时检查 pending 任务的 job（每 2 分钟扫描一次）
        self.scheduler.add_job(
            self._process_pending_tasks,
            IntervalTrigger(minutes=2),
            id="process_pending_tasks",
            name="处理待执行任务",
            replace_existing=True,
        )

        # 添加定时重试失败任务的 job
        self.scheduler.add_job(
            self._retry_failed_tasks,
            IntervalTrigger(minutes=5),
            id="retry_failed_tasks",
            name="重试失败任务",
            replace_existing=True,
        )

        # ContentPilot 自动驾驶：每 30 分钟执行一轮
        self.scheduler.add_job(
            self._run_content_pilot,
            IntervalTrigger(minutes=30),
            id="content_pilot",
            name="ContentPilot 自动生成",
            replace_existing=True,
        )

        self.scheduler.start()
        self._running = True
        logger.info("任务调度器已启动（含 ContentPilot 自动驾驶）")

    def shutdown(self):
        """关闭调度器"""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("任务调度器已关闭")

    async def add_immediate_task(
        self, article_id: int, account_id: int
    ) -> PublishTask:
        """
        添加立即执行的发布任务

        Args:
            article_id: 文章 ID
            account_id: 账号 ID

        Returns:
            PublishTask: 创建的任务
        """
        async with async_session_factory() as session:
            # 检查频率限制
            can_publish, reason = await self._check_rate_limit(
                session, account_id
            )
            if not can_publish:
                raise ValueError(f"频率限制: {reason}")

            # 创建任务
            task = PublishTask(
                article_id=article_id,
                account_id=account_id,
                status="pending",
                scheduled_at=None,  # 立即执行
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)

            logger.info(f"创建立即执行任务: task_id={task.id}")

            # 发布 task_created 事件
            await event_bus.publish("task_created", {
                "task_id": task.id,
                "article_id": article_id,
                "account_id": account_id,
                "scheduled_at": None,
                "mode": "immediate",
            })

            # 立即触发处理
            self.scheduler.add_job(
                self._execute_task,
                DateTrigger(run_date=datetime.now()),
                args=[task.id],
                id=f"immediate_task_{task.id}",
                name=f"立即发布任务 #{task.id}",
                replace_existing=True,
            )

            return task

    async def add_scheduled_task(
        self, article_id: int, account_id: int, scheduled_at: datetime
    ) -> PublishTask:
        """
        添加定时发布任务
        自动添加 ±5 分钟随机抖动以降低被检测风险

        Args:
            article_id: 文章 ID
            account_id: 账号 ID
            scheduled_at: 计划执行时间

        Returns:
            PublishTask: 创建的任务
        """
        # 添加 ±5 分钟随机抖动（反检测）
        jitter_minutes = get_random_jitter_minutes(max_minutes=5)
        jittered_time = scheduled_at + timedelta(minutes=jitter_minutes)

        async with async_session_factory() as session:
            task = PublishTask(
                article_id=article_id,
                account_id=account_id,
                status="pending",
                scheduled_at=jittered_time,
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)

            logger.info(
                f"创建定时任务: task_id={task.id}, "
                f"原始时间={scheduled_at}, "
                f"抖动后={jittered_time} (偏移 {jitter_minutes:+.1f} 分钟)"
            )

            # 发布 task_created 事件
            await event_bus.publish("task_created", {
                "task_id": task.id,
                "article_id": article_id,
                "account_id": account_id,
                "scheduled_at": str(jittered_time),
                "jitter_minutes": round(jitter_minutes, 2),
                "mode": "scheduled",
            })

            # 添加定时触发
            self.scheduler.add_job(
                self._execute_task,
                DateTrigger(run_date=jittered_time),
                args=[task.id],
                id=f"scheduled_task_{task.id}",
                name=f"定时发布任务 #{task.id}",
                replace_existing=True,
            )

            return task

    async def add_batch_tasks(
        self,
        article_ids: list[int],
        account_id: int,
        interval_minutes: int = 10,
    ) -> list[PublishTask]:
        """
        添加批量发布任务
        文章按照间隔时间依次排入队列，每篇自动添加 ±5 分钟随机抖动

        Args:
            article_ids: 文章 ID 列表
            account_id: 账号 ID
            interval_minutes: 每篇间隔（分钟）

        Returns:
            list[PublishTask]: 创建的任务列表
        """
        tasks = []
        base_time = datetime.now()

        async with async_session_factory() as session:
            for idx, article_id in enumerate(article_ids):
                # 基础间隔 + ±5 分钟随机抖动（反检测）
                jitter_minutes = get_random_jitter_minutes(max_minutes=5)
                scheduled_at = base_time + timedelta(
                    minutes=interval_minutes * idx + jitter_minutes
                )

                task = PublishTask(
                    article_id=article_id,
                    account_id=account_id,
                    status="pending",
                    scheduled_at=scheduled_at,
                )
                session.add(task)
                tasks.append(task)

            await session.commit()

            # 刷新获取 ID
            for task in tasks:
                await session.refresh(task)

            # 添加定时触发 & 发布 task_created 事件
            for task in tasks:
                trigger_time = task.scheduled_at or datetime.now()
                self.scheduler.add_job(
                    self._execute_task,
                    DateTrigger(run_date=trigger_time),
                    args=[task.id],
                    id=f"batch_task_{task.id}",
                    name=f"批量发布任务 #{task.id}",
                    replace_existing=True,
                )

                await event_bus.publish("task_created", {
                    "task_id": task.id,
                    "article_id": task.article_id,
                    "account_id": account_id,
                    "scheduled_at": str(trigger_time),
                    "mode": "batch",
                })

        logger.info(
            f"创建批量任务: {len(tasks)} 个, "
            f"间隔 {interval_minutes} 分钟（含随机抖动）"
        )
        return tasks

    async def cancel_task(self, task_id: int) -> None:
        """
        取消任务并移除对应的 APScheduler job

        Args:
            task_id: 任务 ID
        """
        # 尝试移除所有可能的 APScheduler job ID
        for prefix in ("immediate_task_", "scheduled_task_", "batch_task_", "delayed_task_", "retry_task_"):
            job_id = f"{prefix}{task_id}"
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"已移除 APScheduler job: {job_id}")
            except Exception:
                pass  # job 可能不存在，忽略

    async def _execute_task(self, task_id: int):
        """
        执行发布任务

        Args:
            task_id: 任务 ID
        """
        logger.info(f"开始执行任务: task_id={task_id}")

        async with async_session_factory() as session:
            # 获取任务
            task = await session.get(PublishTask, task_id)
            if not task:
                logger.error(f"任务不存在: task_id={task_id}")
                return

            if task.status not in ("pending",):
                logger.warning(
                    f"任务状态不是 pending，跳过执行: "
                    f"task_id={task_id}, status={task.status}"
                )
                return

            # 更新状态为 running
            task.status = "running"
            task.updated_at = datetime.now()
            await session.commit()

            # 获取文章和账号
            article = await session.get(Article, task.article_id)
            account = await session.get(Account, task.account_id)

            if not article:
                task.status = "failed"
                task.error_message = "文章不存在"
                task.updated_at = datetime.now()
                await session.commit()
                return

            if not account:
                task.status = "failed"
                task.error_message = "账号不存在"
                task.updated_at = datetime.now()
                await session.commit()
                return

            if not account.is_active:
                task.status = "failed"
                task.error_message = "账号已禁用"
                task.updated_at = datetime.now()
                await session.commit()
                return

            # 检查是否在活跃时间窗口内
            now = datetime.now()
            if not (settings.ACTIVE_TIME_START <= now.hour < settings.ACTIVE_TIME_END):
                logger.info(
                    f"当前不在活跃时间窗口 "
                    f"({settings.ACTIVE_TIME_START}:00 - {settings.ACTIVE_TIME_END}:00)，"
                    f"延迟执行"
                )
                # 延迟到下一个活跃窗口开始
                task.status = "pending"
                next_active = now.replace(
                    hour=settings.ACTIVE_TIME_START, minute=0, second=0
                )
                if next_active <= now:
                    next_active += timedelta(days=1)
                task.scheduled_at = next_active
                await session.commit()

                self.scheduler.add_job(
                    self._execute_task,
                    DateTrigger(run_date=next_active),
                    args=[task.id],
                    id=f"delayed_task_{task.id}",
                    name=f"延迟发布任务 #{task.id}",
                    replace_existing=True,
                )
                return

            # 创建发布记录
            record = PublishRecord(
                task_id=task.id,
                article_id=task.article_id,
                account_id=task.account_id,
                publish_status="running",
                started_at=datetime.now(),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)

            # 执行发布
            try:
                profile_name = account.browser_profile or f"account_{account.id}"
                result = await zhihu_publisher.publish_article(
                    profile_name=profile_name,
                    title=article.title,
                    content=article.content,
                    tags=article.tags if isinstance(article.tags, list) else [],
                    images=article.images if isinstance(article.images, dict) else None,
                )

                if result["success"]:
                    # 发布成功
                    task.status = "success"
                    task.updated_at = datetime.now()
                    article.status = "published"
                    record.publish_status = "success"
                    record.zhihu_article_url = result.get("article_url")
                    record.screenshot_path = result.get("screenshot_path")
                    record.finished_at = datetime.now()

                    # 记录日志
                    log = SystemLog(
                        event_type="publish",
                        level="info",
                        message=f"文章发布成功: {article.title}",
                        details={
                            "task_id": task.id,
                            "article_id": article.id,
                            "account_id": account.id,
                            "article_url": result.get("article_url"),
                        },
                    )
                    session.add(log)

                    logger.info(f"任务执行成功: task_id={task.id}")

                    # 发布 task_update 事件（成功）
                    await event_bus.publish("task_update", {
                        "task_id": task.id,
                        "status": "success",
                        "article_id": article.id,
                        "account_id": account.id,
                        "article_url": result.get("article_url"),
                    })
                else:
                    # 发布失败
                    task.status = "failed"
                    task.retry_count += 1
                    task.error_message = result.get("message", "未知错误")
                    task.updated_at = datetime.now()
                    record.publish_status = "failed"
                    record.screenshot_path = result.get("screenshot_path")
                    record.finished_at = datetime.now()

                    logger.error(
                        f"任务执行失败: task_id={task.id}, "
                        f"error={result.get('message')}"
                    )

                    # 发布 task_update 事件（失败）
                    await event_bus.publish("task_update", {
                        "task_id": task.id,
                        "status": "failed",
                        "article_id": article.id,
                        "account_id": account.id,
                        "error": result.get("message", "未知错误"),
                        "retry_count": task.retry_count,
                    })

                await session.commit()

            except Exception as e:
                task.status = "failed"
                task.retry_count += 1
                task.error_message = str(e)
                task.updated_at = datetime.now()
                record.publish_status = "failed"
                record.finished_at = datetime.now()
                await session.commit()

                logger.error(f"任务执行异常: task_id={task.id}, error={e}")

                # 发布 task_update 事件（异常）
                await event_bus.publish("task_update", {
                    "task_id": task.id,
                    "status": "failed",
                    "article_id": task.article_id,
                    "account_id": task.account_id,
                    "error": str(e),
                    "retry_count": task.retry_count,
                })

    async def _process_pending_tasks(self):
        """
        处理待执行的任务
        定时扫描 pending 状态且已到执行时间的任务
        """
        async with async_session_factory() as session:
            now = datetime.now()
            stmt = select(PublishTask).where(
                PublishTask.status == "pending",
                (
                    (PublishTask.scheduled_at == None)  # noqa: E711
                    | (PublishTask.scheduled_at <= now)
                ),
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()

            for task in tasks:
                # 检查频率限制
                can_publish, reason = await self._check_rate_limit(
                    session, task.account_id
                )
                if can_publish:
                    # 异步执行任务
                    asyncio.create_task(self._execute_task(task.id))
                    # 两个任务之间至少间隔一小段时间
                    await asyncio.sleep(2)

    @staticmethod
    def _calculate_next_retry_time(
        retry_count: int, last_failure_time: datetime
    ) -> datetime:
        """
        计算下一次重试时间（指数退避 + 随机抖动）

        公式: base_delay * 2^retry_count + random_jitter
        最大延迟不超过 30 分钟

        Args:
            retry_count: 当前重试次数
            last_failure_time: 上次失败的时间

        Returns:
            datetime: 下一次重试的时间点
        """
        delay = RETRY_BASE_DELAY_SECONDS * (2 ** retry_count)
        delay = min(delay, RETRY_MAX_DELAY_SECONDS)
        jitter = random.uniform(0, RETRY_JITTER_MAX_SECONDS)
        total_delay = delay + jitter
        return last_failure_time + timedelta(seconds=total_delay)

    async def _retry_failed_tasks(self):
        """
        重试失败的任务（指数退避策略）

        - 只重试 retry_count 小于最大重试次数的任务
        - 使用公式 base_delay * 2^retry_count + random_jitter 计算退避时间
        - base_delay = 60 秒，jitter = 0~30 秒随机，最大延迟 30 分钟
        - 只有已过退避等待期的任务才会被重新调度
        - 使用 updated_at（最后一次状态变更时间）作为退避基准，确保重试计时准确
        """
        async with async_session_factory() as session:
            stmt = select(PublishTask).where(
                PublishTask.status == "failed",
                PublishTask.retry_count < settings.MAX_RETRY_COUNT,
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()

            now = datetime.now()

            for task in tasks:
                # 使用 updated_at 作为最后失败时间（即退避基准时间）
                # 如果 updated_at 为空（旧数据迁移场景），回退到 created_at
                last_failure_time = task.updated_at or task.created_at

                # retry_count 已经在失败时自增过，所以用 retry_count - 1 计算本次退避
                effective_retry = max(0, task.retry_count - 1)
                next_retry_at = self._calculate_next_retry_time(
                    effective_retry, last_failure_time
                )

                if now < next_retry_at:
                    # 还没到退避时间，跳过
                    remaining = (next_retry_at - now).total_seconds()
                    logger.debug(
                        f"任务 {task.id} 退避中，还需等待 "
                        f"{remaining:.0f} 秒 "
                        f"(retry_count={task.retry_count})"
                    )
                    continue

                logger.info(
                    f"重试任务: task_id={task.id}, "
                    f"retry_count={task.retry_count}, "
                    f"退避延迟已过"
                )
                task.status = "pending"
                task.updated_at = now
                await session.commit()

                # 发布 task_update 事件（重试）
                await event_bus.publish("task_update", {
                    "task_id": task.id,
                    "status": "pending",
                    "retry_count": task.retry_count,
                    "message": "任务已重新排入队列（指数退避）",
                })

    async def _run_content_pilot(self):
        """
        ContentPilot 自动驾驶定时任务
        每 30 分钟检查所有启用的方向，执行自动生成
        只在活跃时间窗口内运行
        """
        now = datetime.now()
        if not (settings.ACTIVE_TIME_START <= now.hour < settings.ACTIVE_TIME_END):
            logger.debug("ContentPilot: 当前不在活跃时间窗口，跳过")
            return

        try:
            from app.core.content_pilot import content_pilot
            results = await content_pilot.run_all_directions()
            total = sum(r.get("articles_generated", 0) for r in results if isinstance(r, dict))
            if total > 0:
                logger.info(f"ContentPilot 自动驾驶完成: 本轮共生成 {total} 篇文章")
        except Exception as e:
            logger.error(f"ContentPilot 自动驾驶异常: {e}")

    async def _check_rate_limit(
        self, session, account_id: int
    ) -> tuple[bool, str]:
        """
        检查发布频率限制

        规则：
        1. 单账号每日发布数量不超过上限
        2. 两次发布之间至少间隔 MIN_PUBLISH_INTERVAL 秒
        3. 必须在活跃时间窗口内

        Args:
            session: 数据库会话
            account_id: 账号 ID

        Returns:
            tuple[bool, str]: (是否允许发布, 原因)
        """
        now = datetime.now()

        # 检查活跃时间窗口
        if not (settings.ACTIVE_TIME_START <= now.hour < settings.ACTIVE_TIME_END):
            return False, (
                f"当前不在活跃时间窗口 "
                f"({settings.ACTIVE_TIME_START}:00 - {settings.ACTIVE_TIME_END}:00)"
            )

        # 获取账号信息
        account = await session.get(Account, account_id)
        if not account:
            return False, "账号不存在"

        daily_limit = account.daily_limit or settings.DAILY_PUBLISH_LIMIT

        # 检查今日已发布数量
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count(PublishTask.id)).where(
            PublishTask.account_id == account_id,
            PublishTask.status == "success",
            PublishTask.created_at >= today_start,
        )
        result = await session.execute(stmt)
        today_count = result.scalar() or 0

        if today_count >= daily_limit:
            return False, f"今日已发布 {today_count} 篇，达到上限 {daily_limit}"

        # 检查最小发布间隔
        min_interval = timedelta(seconds=settings.MIN_PUBLISH_INTERVAL)
        stmt = (
            select(PublishTask.created_at)
            .where(
                PublishTask.account_id == account_id,
                PublishTask.status.in_(["success", "running"]),
            )
            .order_by(PublishTask.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        last_publish = result.scalar()

        if last_publish and (now - last_publish) < min_interval:
            remaining = min_interval - (now - last_publish)
            return False, f"需要等待 {int(remaining.total_seconds())} 秒后才能发布"

        return True, "OK"


# 全局单例
task_scheduler = TaskScheduler()
