import React, { useState, useEffect, useMemo } from 'react';
import { Calendar as AntCalendar, Badge, Typography, Tag, Popover, Spin } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { taskAPI } from '../../services/api';
import { colors } from '../../styles/theme';
import type { PublishTask } from '../../utils/types';

const { Text } = Typography;

const statusBadgeMap: Record<string, 'success' | 'processing' | 'error' | 'default' | 'warning'> = {
  success: 'success',
  running: 'processing',
  pending: 'default',
  failed: 'error',
  cancelled: 'warning',
};

const statusTextMap: Record<string, string> = {
  success: '成功',
  running: '运行中',
  pending: '等待中',
  failed: '失败',
  cancelled: '已取消',
};

interface CalendarProps {
  /** Incremented externally to force a data refresh (e.g. after SSE event). */
  refreshKey?: number;
}

const Calendar: React.FC<CalendarProps> = ({ refreshKey }) => {
  const [tasks, setTasks] = useState<PublishTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(dayjs());

  const fetchCalendarTasks = async (date: Dayjs) => {
    setLoading(true);
    try {
      const start = date.startOf('month').format('YYYY-MM-DD');
      const end = date.endOf('month').format('YYYY-MM-DD');
      const res = await taskAPI.calendar(start, end);
      setTasks(res.data);
    } catch {
      // silently fail -- the error is already logged by the axios interceptor
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalendarTasks(currentMonth);
  }, [currentMonth]);

  // Re-fetch when the parent signals a refresh (e.g. SSE event received).
  useEffect(() => {
    if (refreshKey && refreshKey > 0) {
      fetchCalendarTasks(currentMonth);
    }
  }, [refreshKey]);

  // Group tasks by date string (YYYY-MM-DD) for O(1) look-ups in render.
  const tasksByDate = useMemo(() => {
    const map: Record<string, PublishTask[]> = {};
    tasks.forEach((task) => {
      const date = task.scheduled_at
        ? dayjs(task.scheduled_at).format('YYYY-MM-DD')
        : dayjs(task.created_at).format('YYYY-MM-DD');
      if (!map[date]) map[date] = [];
      map[date].push(task);
    });
    return map;
  }, [tasks]);

  const dateCellRender = (value: Dayjs) => {
    const dateStr = value.format('YYYY-MM-DD');
    const dayTasks = tasksByDate[dateStr];
    if (!dayTasks || dayTasks.length === 0) return null;

    return (
      <Popover
        title={`${dateStr} 任务 (${dayTasks.length})`}
        content={
          <div style={{ maxHeight: 200, overflowY: 'auto', maxWidth: 300 }}>
            {dayTasks.map((t) => (
              <div key={t.id} style={{ marginBottom: 8 }}>
                <Badge status={statusBadgeMap[t.status] || 'default'} />
                <Text style={{ marginLeft: 4, fontSize: 12 }}>
                  {t.article_title || `文章 #${t.article_id}`}
                </Text>
                <Tag
                  style={{ marginLeft: 4, fontSize: 11 }}
                  color={
                    t.status === 'success'
                      ? 'green'
                      : t.status === 'failed'
                        ? 'red'
                        : t.status === 'running'
                          ? 'orange'
                          : 'blue'
                  }
                >
                  {statusTextMap[t.status] || t.status}
                </Tag>
              </div>
            ))}
          </div>
        }
        trigger="hover"
      >
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {dayTasks.slice(0, 3).map((t) => (
            <li key={t.id} style={{ marginBottom: 2 }}>
              <Badge
                status={statusBadgeMap[t.status] || 'default'}
                text={
                  <Text
                    style={{ fontSize: 11, color: colors.textPrimary }}
                    ellipsis
                  >
                    {t.article_title || `#${t.article_id}`}
                  </Text>
                }
              />
            </li>
          ))}
          {dayTasks.length > 3 && (
            <li>
              <Text style={{ fontSize: 11, color: colors.textTertiary }}>
                +{dayTasks.length - 3} 更多
              </Text>
            </li>
          )}
        </ul>
      </Popover>
    );
  };

  return (
    <Spin spinning={loading}>
      <AntCalendar
        cellRender={(current, info) => {
          if (info.type === 'date') return dateCellRender(current);
          return null;
        }}
        onPanelChange={(date) => setCurrentMonth(date)}
        style={{
          background: colors.bgContainer,
          borderRadius: 12,
        }}
      />
    </Spin>
  );
};

export default Calendar;
