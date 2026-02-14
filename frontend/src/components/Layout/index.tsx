import React, { useState, useMemo } from 'react';
import { Layout, Menu, Typography, Avatar, Tooltip } from 'antd';
import {
  DashboardOutlined,
  EditOutlined,
  FileTextOutlined,
  UserOutlined,
  ScheduleOutlined,
  HistoryOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  KeyOutlined,
  RocketOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import NotificationCenter from '../NotificationCenter';
import { colors, gradients, layout } from '../../styles/theme';

const { Sider, Header, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/generate', icon: <EditOutlined />, label: 'AI 文章生成' },
  { key: '/pilot', icon: <RocketOutlined />, label: '自动驾驶' },
  { key: '/qa', icon: <QuestionCircleOutlined />, label: '知乎问答' },
  { key: '/articles', icon: <FileTextOutlined />, label: '文章管理' },
  { key: '/accounts', icon: <UserOutlined />, label: '账号管理' },
  { key: '/tasks', icon: <ScheduleOutlined />, label: '任务调度' },
  { key: '/history', icon: <HistoryOutlined />, label: '发布历史' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
];

interface AppLayoutProps {
  children: React.ReactNode;
}

const shortcutHintContent = (
  <div style={{ fontSize: 12, lineHeight: '22px', padding: '4px 0' }}>
    {menuItems.map((item, i) => (
      <div key={item.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <kbd style={{
          background: colors.bgActive,
          padding: '1px 6px',
          borderRadius: 4,
          fontSize: 11,
          fontFamily: 'monospace',
          border: `1px solid ${colors.border}`,
          color: colors.textSecondary,
          minWidth: 42,
          textAlign: 'center',
        }}>Alt+{i + 1}</kbd>
        <span style={{ color: colors.textSecondary }}>{item.label}</span>
      </div>
    ))}
  </div>
);

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  useKeyboardShortcuts();

  const selectedKey = useMemo(() => {
    const path = location.pathname;
    const found = menuItems.find((item) => item.key === path);
    if (found) return [found.key];
    const prefix = menuItems.find((item) => item.key !== '/' && path.startsWith(item.key));
    return prefix ? [prefix.key] : ['/'];
  }, [location.pathname]);

  const currentTitle = useMemo(
    () => menuItems.find((item) => selectedKey.includes(item.key))?.label || '仪表盘',
    [selectedKey]
  );

  const siderWidth = collapsed ? layout.sidebarCollapsedWidth : layout.sidebarWidth;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={layout.sidebarWidth}
        collapsedWidth={layout.sidebarCollapsedWidth}
        style={{
          background: gradients.sidebar,
          borderRight: `1px solid ${colors.border}`,
          overflow: 'hidden',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Logo */}
        <div
          style={{
            height: layout.headerHeight,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? '0' : '0 20px',
            borderBottom: `1px solid ${colors.border}`,
            cursor: 'pointer',
            position: 'relative',
            overflow: 'hidden',
          }}
          onClick={() => navigate('/')}
        >
          {/* Logo glow background */}
          <div style={{
            position: 'absolute',
            top: '50%',
            left: collapsed ? '50%' : 28,
            transform: collapsed ? 'translate(-50%, -50%)' : 'translateY(-50%)',
            width: 36,
            height: 36,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(22,119,255,0.2) 0%, transparent 70%)',
            filter: 'blur(4px)',
            pointerEvents: 'none',
          }} />
          <div style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 34,
            height: 34,
            borderRadius: 8,
            background: 'linear-gradient(135deg, rgba(22,119,255,0.2), rgba(114,46,209,0.2))',
            border: '1px solid rgba(22,119,255,0.3)',
            marginRight: collapsed ? 0 : 12,
            fontSize: 18,
            color: colors.primary,
            flexShrink: 0,
          }}>
            <RocketOutlined />
          </div>
          {!collapsed && (
            <div style={{ overflow: 'hidden' }}>
              <div style={{
                fontSize: 15,
                fontWeight: 700,
                color: colors.textPrimary,
                whiteSpace: 'nowrap',
                letterSpacing: '0.5px',
                lineHeight: 1.2,
              }}>
                AutoPilot
              </div>
              <div style={{
                fontSize: 10,
                color: colors.textTertiary,
                whiteSpace: 'nowrap',
                letterSpacing: '1px',
                textTransform: 'uppercase',
                marginTop: 1,
              }}>
                Content Engine
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
          <Menu
            mode="inline"
            selectedKeys={selectedKey}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            className="sidebar-menu"
            style={{
              background: 'transparent',
              borderRight: 'none',
            }}
          />
        </div>

        {/* Shortcut hint */}
        <div style={{
          padding: '12px 0',
          display: 'flex',
          justifyContent: 'center',
          borderTop: `1px solid ${colors.border}`,
        }}>
          <Tooltip title={shortcutHintContent} placement="right" overlayStyle={{ maxWidth: 240 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: 'pointer',
                color: colors.textDisabled,
                fontSize: 12,
                padding: '6px 12px',
                borderRadius: 6,
                transition: 'all 0.25s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = colors.textSecondary;
                e.currentTarget.style.background = colors.bgHover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = colors.textDisabled;
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <KeyOutlined />
              {!collapsed && <span>快捷键</span>}
            </div>
          </Tooltip>
        </div>
      </Sider>

      {/* Content Layout */}
      <Layout
        style={{
          marginLeft: siderWidth,
          transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          background: colors.bgLayout,
          minHeight: '100vh',
        }}
      >
        {/* Header */}
        <Header
          style={{
            background: colors.glassBg,
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${colors.glassBorder}`,
            position: 'sticky',
            top: 0,
            zIndex: 99,
            height: layout.headerHeight,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Collapse toggle */}
            <div
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: 16,
                cursor: 'pointer',
                color: colors.textTertiary,
                padding: '6px 8px',
                borderRadius: 6,
                transition: 'all 0.25s ease',
                display: 'flex',
                alignItems: 'center',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = colors.primary;
                e.currentTarget.style.background = 'rgba(22,119,255,0.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = colors.textTertiary;
                e.currentTarget.style.background = 'transparent';
              }}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </div>

            {/* Page title */}
            <Text style={{
              fontSize: 16,
              fontWeight: 600,
              color: colors.textPrimary,
              letterSpacing: '0.2px',
            }}>
              {currentTitle}
            </Text>
          </div>

          {/* Right section */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <NotificationCenter />
            <div style={{
              height: 20,
              width: 1,
              background: colors.border,
              margin: '0 4px',
            }} />
            <Text style={{
              color: colors.textTertiary,
              fontSize: 13,
              marginRight: 4,
            }}>
              Admin
            </Text>
            <Avatar
              size={30}
              icon={<UserOutlined />}
              style={{
                background: 'linear-gradient(135deg, #1677ff, #722ed1)',
                border: '2px solid rgba(22,119,255,0.3)',
                fontSize: 13,
              }}
            />
          </div>
        </Header>

        {/* Main Content */}
        <Content
          className="page-enter"
          style={{
            margin: layout.contentPadding,
            minHeight: `calc(100vh - ${layout.headerHeight + layout.contentPadding * 2}px)`,
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
