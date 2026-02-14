import React, { useState } from 'react';
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
  ThunderboltOutlined,
  KeyOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import NotificationCenter from '../NotificationCenter';

const { Sider, Header, Content } = Layout;
const { Title } = Typography;

/** 侧边栏菜单项配置 */
const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/generate', icon: <EditOutlined />, label: 'AI 生成文章' },
  { key: '/pilot', icon: <RocketOutlined />, label: '自动驾驶' },
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
  <div style={{ fontSize: 12, lineHeight: '20px' }}>
    <div><b>Alt+1</b> 仪表盘</div>
    <div><b>Alt+2</b> AI 生成文章</div>
    <div><b>Alt+3</b> 自动驾驶</div>
    <div><b>Alt+4</b> 文章管理</div>
    <div><b>Alt+5</b> 任务调度</div>
    <div><b>Alt+6</b> 发布历史</div>
    <div><b>Alt+7</b> 账号管理</div>
    <div><b>Alt+8</b> 系统设置</div>
  </div>
);

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Register global keyboard shortcuts
  useKeyboardShortcuts();

  /** 获取当前选中的菜单项 */
  const getSelectedKey = () => {
    const path = location.pathname;
    // 精确匹配
    const found = menuItems.find((item) => item.key === path);
    if (found) return [found.key];
    // 前缀匹配
    const prefix = menuItems.find(
      (item) => item.key !== '/' && path.startsWith(item.key)
    );
    return prefix ? [prefix.key] : ['/'];
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={240}
        style={{
          background: '#1a1a2e',
          borderRight: '1px solid #2a2a3e',
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
        }}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? '0' : '0 20px',
            borderBottom: '1px solid #2a2a3e',
            cursor: 'pointer',
          }}
          onClick={() => navigate('/')}
        >
          <ThunderboltOutlined
            style={{
              fontSize: 24,
              color: '#1677ff',
              marginRight: collapsed ? 0 : 12,
            }}
          />
          {!collapsed && (
            <Title
              level={4}
              style={{
                margin: 0,
                color: '#e8e8e8',
                fontSize: 16,
                whiteSpace: 'nowrap',
              }}
            >
              知乎自动发文
            </Title>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={getSelectedKey()}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: 'transparent',
            borderRight: 'none',
            marginTop: 8,
          }}
        />

        {/* 快捷键提示 */}
        <div
          style={{
            position: 'absolute',
            bottom: 16,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <Tooltip title={shortcutHintContent} placement="right" overlayStyle={{ maxWidth: 220 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: 'pointer',
                color: '#666',
                fontSize: 12,
                padding: '4px 12px',
                borderRadius: 4,
                transition: 'color 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#a0a0a0';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#666';
              }}
            >
              <KeyOutlined />
              {!collapsed && <span>快捷键</span>}
            </div>
          </Tooltip>
        </div>
      </Sider>

      {/* 右侧内容区 */}
      <Layout
        style={{
          marginLeft: collapsed ? 80 : 240,
          transition: 'margin-left 0.2s',
          background: '#141414',
        }}
      >
        {/* 顶部导航栏 */}
        <Header
          style={{
            background: '#1a1a2e',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #2a2a3e',
            position: 'sticky',
            top: 0,
            zIndex: 99,
            height: 64,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center' }}>
            {/* 折叠按钮 */}
            <div
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: 18,
                cursor: 'pointer',
                color: '#a0a0a0',
                marginRight: 16,
                padding: '4px 8px',
                borderRadius: 4,
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#1677ff';
                e.currentTarget.style.background = 'rgba(22,119,255,0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#a0a0a0';
                e.currentTarget.style.background = 'transparent';
              }}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </div>
            {/* 当前页面标题 */}
            <span style={{ color: '#e8e8e8', fontSize: 16, fontWeight: 500 }}>
              {menuItems.find((item) => getSelectedKey().includes(item.key))
                ?.label || '仪表盘'}
            </span>
          </div>

          {/* 右侧：通知 + 用户信息 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <NotificationCenter />
            <span style={{ color: '#a0a0a0', fontSize: 13 }}>管理员</span>
            <Avatar
              size={32}
              icon={<UserOutlined />}
              style={{ background: '#1677ff' }}
            />
          </div>
        </Header>

        {/* 主内容区 */}
        <Content
          style={{
            margin: 24,
            minHeight: 'calc(100vh - 112px)',
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
