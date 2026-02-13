import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Badge,
  Popover,
  List,
  Typography,
  Button,
  Tag,
  Empty,
  Space,
  Spin,
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

const { Text } = Typography;

interface NotificationItem {
  id: number;
  title: string;
  content: string | null;
  type: string; // info, success, warning, error
  is_read: boolean;
  created_at: string | null;
}

/** Type icon mapping */
const typeIconMap: Record<string, React.ReactNode> = {
  info: <InfoCircleOutlined style={{ color: '#1677ff' }} />,
  success: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  warning: <WarningOutlined style={{ color: '#faad14' }} />,
  error: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
};

/** Type color mapping */
const typeColorMap: Record<string, string> = {
  info: 'blue',
  success: 'green',
  warning: 'orange',
  error: 'red',
};

const NotificationCenter: React.FC = () => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const openRef = useRef(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  /** Fetch unread count */
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await notificationAPI.unreadCount();
      setUnreadCount(res.data.count);
    } catch {
      // silently fail
    }
  }, []);

  /** Fetch notifications list */
  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationAPI.list({ page: 1, page_size: 20 });
      setNotifications(res.data.items);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  /** Mark single notification as read */
  const handleMarkRead = async (id: number) => {
    try {
      await notificationAPI.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // silently fail
    }
  };

  /** Mark all as read */
  const handleMarkAllRead = async () => {
    try {
      await notificationAPI.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // silently fail
    }
  };

  /** Setup SSE connection for real-time updates */
  useEffect(() => {
    fetchUnreadCount();

    // Connect to SSE event stream
    try {
      const es = new EventSource('/api/events/stream');
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // If we get a notification-related event, refresh the count
          if (
            data.type === 'notification_created' ||
            data.type === 'task_update' ||
            data.type === 'task_created' ||
            data.type === 'account_status_change'
          ) {
            fetchUnreadCount();
            if (openRef.current) {
              fetchNotifications();
            }
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        // SSE connection error - will auto-reconnect
      };
    } catch {
      // EventSource not supported or other error
    }

    // Poll unread count every 30 seconds as fallback
    const pollInterval = setInterval(fetchUnreadCount, 30000);

    return () => {
      clearInterval(pollInterval);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [fetchUnreadCount, fetchNotifications]);

  /** When popover opens, fetch notifications */
  const handleOpenChange = (visible: boolean) => {
    setOpen(visible);
    openRef.current = visible;
    if (visible) {
      fetchNotifications();
    }
  };

  /** Format time display */
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
    } catch {
      return '';
    }
  };

  const content = (
    <div style={{ width: 360, maxHeight: 450, overflow: 'auto' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 0 12px',
          borderBottom: '1px solid #2a2a3e',
          marginBottom: 8,
        }}
      >
        <Text strong style={{ color: '#e8e8e8', fontSize: 15 }}>
          通知中心
        </Text>
        {unreadCount > 0 && (
          <Button
            type="link"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleMarkAllRead}
            style={{ color: '#1677ff', fontSize: 12 }}
          >
            全部已读
          </Button>
        )}
      </div>

      {/* Notifications List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin size="small" />
        </div>
      ) : notifications.length === 0 ? (
        <Empty
          description={<Text style={{ color: '#666' }}>暂无通知</Text>}
          style={{ padding: '24px 0' }}
        />
      ) : (
        <List
          dataSource={notifications}
          renderItem={(item) => (
            <List.Item
              style={{
                padding: '10px 4px',
                borderBottom: '1px solid #1a1a2e',
                background: item.is_read ? 'transparent' : 'rgba(22, 119, 255, 0.04)',
                cursor: item.is_read ? 'default' : 'pointer',
                borderRadius: 4,
              }}
              onClick={() => {
                if (!item.is_read) handleMarkRead(item.id);
              }}
            >
              <List.Item.Meta
                avatar={
                  <div style={{ paddingTop: 4 }}>
                    {typeIconMap[item.type] || typeIconMap.info}
                  </div>
                }
                title={
                  <Space size={8}>
                    <Text
                      style={{
                        color: item.is_read ? '#a0a0a0' : '#e8e8e8',
                        fontSize: 13,
                        fontWeight: item.is_read ? 400 : 500,
                      }}
                    >
                      {item.title}
                    </Text>
                    {!item.is_read && (
                      <Badge dot status="processing" />
                    )}
                  </Space>
                }
                description={
                  <div>
                    {item.content && (
                      <Text
                        style={{ color: '#666', fontSize: 12, display: 'block' }}
                        ellipsis={{ tooltip: item.content }}
                      >
                        {item.content}
                      </Text>
                    )}
                    <Text style={{ color: '#555', fontSize: 11 }}>
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
        background: '#1f1f1f',
        border: '1px solid #2a2a3e',
        borderRadius: 8,
        padding: '8px 12px',
      }}
    >
      <div
        style={{
          cursor: 'pointer',
          padding: '4px 8px',
          borderRadius: 4,
          transition: 'all 0.2s',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        <Badge count={unreadCount} size="small" offset={[-2, 2]}>
          <BellOutlined style={{ fontSize: 18, color: '#a0a0a0' }} />
        </Badge>
      </div>
    </Popover>
  );
};

export default NotificationCenter;
