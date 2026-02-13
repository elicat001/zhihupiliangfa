"""
SSE 实时事件推送模块
基于 Server-Sent Events 提供实时任务状态更新、账号状态变更等事件流

改进点：
- 添加 heartbeat 心跳机制，防止连接被代理/浏览器超时断开
- subscribe 使用 asyncio.wait_for 超时机制实现心跳
- 事件格式包含 event: 字段以支持前端 addEventListener
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

# 心跳间隔（秒）—— 每 15 秒发送一次 SSE 注释行作为 keepalive
HEARTBEAT_INTERVAL_SECONDS = 15


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

    @property
    def subscriber_count(self) -> int:
        """当前订阅者数量"""
        return len(self._subscribers)

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
    将事件总线中的事件格式化为 SSE 协议格式。

    功能：
    - 发送初始连接确认
    - 转发事件总线中的事件（使用 data-only 格式，兼容前端 onmessage）
    - 定期发送心跳注释行（: heartbeat），防止连接被代理/浏览器超时断开

    注意：
    - 使用不带 event: 字段的格式，确保浏览器 EventSource.onmessage 能接收
    - 事件类型通过 data JSON 中的 "type" 字段区分
    - 心跳使用 SSE 注释行（以 : 开头），浏览器会忽略但不会断开连接
    """
    # 发送初始连接确认
    connected_payload = json.dumps(
        {"type": "connected", "message": "SSE 连接已建立"},
        ensure_ascii=False,
    )
    yield f"data: {connected_payload}\n\n"

    # 创建订阅队列
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    async with event_bus._lock:
        event_bus._subscribers.append(queue)

    logger.info(f"新的 SSE 订阅者已连接，当前订阅者数: {event_bus.subscriber_count}")

    try:
        while True:
            try:
                # 等待事件，超时则发送心跳
                event = await asyncio.wait_for(
                    queue.get(), timeout=HEARTBEAT_INTERVAL_SECONDS
                )
                payload = json.dumps(event, ensure_ascii=False, default=str)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                # 超时未收到事件，发送 SSE 注释行作为心跳 keepalive
                yield f": heartbeat {time.time()}\n\n"
    except asyncio.CancelledError:
        pass
    except GeneratorExit:
        pass
    finally:
        async with event_bus._lock:
            if queue in event_bus._subscribers:
                event_bus._subscribers.remove(queue)
        logger.info(f"SSE 订阅者已断开，剩余订阅者数: {event_bus.subscriber_count}")


@router.get("/stream", summary="SSE 实时事件流")
async def event_stream():
    """
    SSE 端点 -- 实时推送系统事件

    事件类型：
    - `connected`: 连接建立确认
    - `task_update`: 任务状态更新（成功/失败/重试）
    - `task_created`: 新任务创建
    - `task_cancelled`: 任务被取消
    - `account_status_change`: 账号状态变更
    - `notification_created`: 新通知

    事件格式 (SSE):
    ```
    event: task_update
    data: {"type": "task_update", "task_id": 1, "status": "success", ...}

    ```

    心跳机制：
    - 每 15 秒发送一次 SSE 注释行 (`: heartbeat ...`) 防止连接超时
    """
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Access-Control-Allow-Origin": "*",
        },
    )
