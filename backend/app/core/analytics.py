"""
数据分析引擎
分析发布历史数据，提供最佳发布时间建议
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import PublishTask, PublishRecord

logger = logging.getLogger(__name__)

# 知乎用户活跃时段权重（基于平台数据）
ZHIHU_ACTIVE_HOURS = {
    8: 0.7,   # 早间通勤
    9: 0.8,
    10: 0.6,
    11: 0.5,
    12: 0.9,  # 午间高峰
    13: 0.8,
    14: 0.5,
    15: 0.4,
    16: 0.5,
    17: 0.6,
    18: 0.7,
    19: 0.9,  # 晚间高峰
    20: 1.0,  # 黄金时段
    21: 0.95,
    22: 0.8,
    23: 0.5,
}


async def get_optimal_publish_times(
    db: AsyncSession,
    account_id: int | None = None,
    days: int = 30,
) -> list[dict]:
    """
    分析历史数据并结合知乎活跃时段，推荐最佳发布时间

    算法说明:
      1. 查询最近 N 天内所有 PublishRecord，按小时分组统计总数与成功数
      2. 综合评分 = 知乎活跃权重 * 0.6 + 历史成功率 * 0.4
      3. 如果某小时无历史数据，则仅使用知乎活跃权重
      4. 返回 Top 5 推荐时段

    Args:
        db: 异步数据库会话
        account_id: 可选，按账号筛选
        days: 分析的天数范围，默认 30 天

    Returns:
        list of {"hour": int, "score": float, "reason": str}
    """
    # 1. 查询历史发布记录，按小时分组
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 使用 SQLite 的 strftime 提取小时
    hour_col = func.strftime('%H', PublishRecord.started_at).label('hour')

    # 用 case 表达式统计成功次数（publish_status 为模型中的实际列名）
    success_case = case(
        (PublishRecord.publish_status == 'success', 1),
        else_=0,
    )

    query = (
        select(
            hour_col,
            func.count().label('total'),
            func.sum(success_case).label('success_count'),
        )
        .where(PublishRecord.started_at >= since)
        .group_by('hour')
    )

    # 如果指定了账号，直接在 PublishRecord 上筛选（模型自带 account_id 列）
    if account_id is not None:
        query = query.where(PublishRecord.account_id == account_id)

    result = await db.execute(query)
    rows = result.all()

    # 解析结果：hour 字符串 -> int
    history: dict[int, dict] = {}
    for row in rows:
        h = int(row.hour)
        history[h] = {
            "total": row.total,
            "success": row.success_count or 0,
        }

    # 2. 综合评分：知乎活跃权重 * 0.6 + 历史成功率 * 0.4
    scores: list[dict] = []
    for hour in range(24):
        zhihu_weight = ZHIHU_ACTIVE_HOURS.get(hour, 0.1)

        if hour in history and history[hour]["total"] > 0:
            success_rate = history[hour]["success"] / history[hour]["total"]
            combined = zhihu_weight * 0.6 + success_rate * 0.4
            reason = f"知乎活跃度 {zhihu_weight:.0%}，历史成功率 {success_rate:.0%}"
        else:
            combined = zhihu_weight * 0.6
            reason = f"知乎活跃度 {zhihu_weight:.0%}（暂无历史数据）"

        scores.append({
            "hour": hour,
            "score": round(combined, 2),
            "reason": reason,
        })

    # 3. 按得分降序排列，取 Top 5
    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:5]


async def get_publish_hour_distribution(
    db: AsyncSession,
    account_id: int | None = None,
    days: int = 30,
) -> list[dict]:
    """
    获取发布时段分布（用于可视化图表）

    Returns:
        list of {"hour": int, "total": int, "success": int, "failed": int}
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    hour_col = func.strftime('%H', PublishRecord.started_at).label('hour')

    success_case = case(
        (PublishRecord.publish_status == 'success', 1),
        else_=0,
    )
    failed_case = case(
        (PublishRecord.publish_status == 'failed', 1),
        else_=0,
    )

    query = (
        select(
            hour_col,
            func.count().label('total'),
            func.sum(success_case).label('success'),
            func.sum(failed_case).label('failed'),
        )
        .where(PublishRecord.started_at >= since)
        .group_by('hour')
    )

    if account_id is not None:
        query = query.where(PublishRecord.account_id == account_id)

    result = await db.execute(query)
    rows = result.all()

    # 构造 24 小时完整分布
    dist = {h: {"hour": h, "total": 0, "success": 0, "failed": 0} for h in range(24)}
    for row in rows:
        h = int(row.hour)
        dist[h] = {
            "hour": h,
            "total": row.total,
            "success": row.success or 0,
            "failed": row.failed or 0,
        }

    return [dist[h] for h in range(24)]
