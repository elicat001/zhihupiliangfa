"""
SSE 实时事件推送模块
基于 Server-Sent Events 提供实时任务状态更新、账号状态变更等事件流
"""

import asyncio
import json
import logging
import time
from typing import AsyncIterator

from fastapi import APIRouter
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["事件推送"])


class EventBus:
    """
    事件总线
    基于 asyncio.Queue 实现的发布-订阅模式，
    支持多个 SSE 客户端同时订阅。
    """

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def publish(self, event_type: str, data: dict) -> None:
        """
        发布事件到所有已连接的订阅者

        Args:
            event_type: 事件类型，如 task_update / task_created / account_status_change
            data: 事件负载（字典）
        """
        message = {
            "type": event_type,
            "timestamp": time.time(),
            **data,
        }
        async with self._lock:
            dead_queues = []
            for queue in self._subscribers:
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    # 队列满了，说明客户端可能卡住，标记为死连接
                    dead_queues.append(queue)

            # 清理死连接
            for q in dead_queues:
                self._subscribers.remove(q)
                logger.warning("移除一个积压过多的 SSE 订阅者")

        logger.debug(f"事件已发布: type={event_type}, subscribers={len(self._subscribers)}")

    async def subscribe(self) -> AsyncIterator[dict]:
        """
        订阅事件流

        Returns:
            AsyncIterator[dict]: 异步事件迭代器
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.append(queue)

        logger.info(f"新的 SSE 订阅者已连接，当前订阅者数: {len(self._subscribers)}")

        try:
            while True:
                event = await queue.get()
                yield event
        except asyncio.CancelledError:
            pass
        finally:
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)
            logger.info(f"SSE 订阅者已断开，剩余订阅者数: {len(self._subscribers)}")


# 全局事件总线单例
event_bus = EventBus()


async def _event_generator() -> AsyncIterator[str]:
    """
    SSE 事件生成器
    将事件总线中的事件格式化为 SSE 协议格式
    """
    # 发送初始连接确认
    yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE 连接已建立'})}\n\n"

    async for event in event_bus.subscribe():
        payload = json.dumps(event, ensure_ascii=False, default=str)
        yield f"data: {payload}\n\n"


@router.get("/stream", summary="SSE 实时事件流")
async def event_stream():
    """
    SSE 端点 —— 实时推送系统事件

    事件类型：
    - `task_update`: 任务状态更新（成功/失败/重试）
    - `task_created`: 新任务创建
    - `account_status_change`: 账号状态变更

    事件格式:
    ```
    data: {"type": "task_update", "task_id": 1, "status": "success", ...}\n\n
    ```
    """
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
