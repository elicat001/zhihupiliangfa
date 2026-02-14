import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Badge,
  Popover,
  List,
  Typography,
  Button,
  Space,
  Spin,
  Empty,
} from 'antd';
import {
  BellOutlined,
  CheckOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { notificationAPI } from '../../services/api';
import { colors } from '../../styles/theme';

const { Text } = Typography;

interface NotificationItem {
  id: number;
  title: string;
  content: string | null;
  type: string;
  is_read: boolean;
  created_at: string | null;
}

const typeIconMap: Record<string, React.ReactNode> = {
  info: <InfoCircleOutlined style={{ color: colors.primary }} />,
  success: <CheckCircleOutlined style={{ color: colors.success }} />,
  warning: <WarningOutlined style={{ color: colors.warning }} />,
  error: <CloseCircleOutlined style={{ color: colors.error }} />,
};

const NotificationCenter: React.FC = () => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const openRef = useRef(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await notificationAPI.unreadCount();
      setUnreadCount(res.data.count);
    } catch { /* silently fail */ }
  }, []);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationAPI.list({ page: 1, page_size: 20 });
      setNotifications(res.data.items);
    } catch { /* silently fail */ }
    finally { setLoading(false); }
  }, []);

  const handleMarkRead = async (id: number) => {
    try {
      await notificationAPI.markRead(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch { /* silently fail */ }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationAPI.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch { /* silently fail */ }
  };

  useEffect(() => {
    fetchUnreadCount();
    try {
      const es = new EventSource('/api/events/stream');
      eventSourceRef.current = es;
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (['notification_created', 'task_update', 'task_created', 'account_status_change'].includes(data.type)) {
            fetchUnreadCount();
            if (openRef.current) fetchNotifications();
          }
        } catch { /* ignore */ }
      };
      es.onerror = () => {};
    } catch { /* EventSource not supported */ }

    const pollInterval = setInterval(fetchUnreadCount, 30000);
    return () => {
      clearInterval(pollInterval);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [fetchUnreadCount, fetchNotifications]);

  const handleOpenChange = (visible: boolean) => {
    setOpen(visible);
    openRef.current = visible;
    if (visible) fetchNotifications();
  };

  const formatTime = (timeStr: string | null) => {
    if (!timeStr) return '';
    try {
      const date = new Date(timeStr);
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const minutes = Math.floor(diff / 60000);
      const hours = Math.floor(diff / 3600000);
      const days = Math.floor(diff / 86400000);
      if (minutes < 1) return '刚刚';
      if (minutes < 60) return `${minutes} 分钟前`;
      if (hours < 24) return `${hours} 小时前`;
      if (days < 7) return `${days} 天前`;
      return date.toLocaleString('zh-CN');
    } catch { return ''; }
  };

  const content = (
    <div style={{ width: 360, maxHeight: 450, overflow: 'auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 0 12px',
        borderBottom: `1px solid ${colors.border}`,
        marginBottom: 8,
      }}>
        <Text strong style={{ color: colors.textPrimary, fontSize: 15 }}>
          通知中心
        </Text>
        {unreadCount > 0 && (
          <Button
            type="link"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleMarkAllRead}
            style={{ color: colors.primary, fontSize: 12 }}
          >
            全部已读
          </Button>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin size="small" />
        </div>
      ) : notifications.length === 0 ? (
        <Empty
          description={<Text style={{ color: colors.textTertiary }}>暂无通知</Text>}
          style={{ padding: '24px 0' }}
        />
      ) : (
        <List
          dataSource={notifications}
          renderItem={(item) => (
            <List.Item
              style={{
                padding: '10px 8px',
                borderBottom: `1px solid ${colors.bgHover}`,
                background: item.is_read ? 'transparent' : 'rgba(22, 119, 255, 0.04)',
                cursor: item.is_read ? 'default' : 'pointer',
                borderRadius: 6,
                marginBottom: 2,
                transition: 'all 0.2s ease',
              }}
              onClick={() => { if (!item.is_read) handleMarkRead(item.id); }}
            >
              <List.Item.Meta
                avatar={<div style={{ paddingTop: 4 }}>{typeIconMap[item.type] || typeIconMap.info}</div>}
                title={
                  <Space size={8}>
                    <Text style={{
                      color: item.is_read ? colors.textSecondary : colors.textPrimary,
                      fontSize: 13,
                      fontWeight: item.is_read ? 400 : 500,
                    }}>
                      {item.title}
                    </Text>
                    {!item.is_read && <Badge dot status="processing" />}
                  </Space>
                }
                description={
                  <div>
                    {item.content && (
                      <Text
                        style={{ color: colors.textTertiary, fontSize: 12, display: 'block' }}
                        ellipsis={{ tooltip: item.content }}
                      >
                        {item.content}
                      </Text>
                    )}
                    <Text style={{ color: colors.textDisabled, fontSize: 11 }}>
                      {formatTime(item.created_at)}
                    </Text>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      placement="bottomRight"
      open={open}
      onOpenChange={handleOpenChange}
      overlayStyle={{ padding: 0 }}
      overlayInnerStyle={{
        background: colors.bgElevated,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        padding: '8px 12px',
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.4)',
      }}
    >
      <div style={{
        cursor: 'pointer',
        padding: '6px 8px',
        borderRadius: 6,
        transition: 'all 0.25s ease',
        display: 'flex',
        alignItems: 'center',
      }}>
        <Badge count={unreadCount} size="small" offset={[-2, 2]}>
          <BellOutlined style={{ fontSize: 17, color: colors.textSecondary }} />
        </Badge>
      </div>
    </Popover>
  );
};

export default NotificationCenter;
