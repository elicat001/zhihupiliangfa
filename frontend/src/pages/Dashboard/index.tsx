import React, { useEffect, useState } from 'react';
import {
  Card,
  Col,
  Row,
  Statistic,
  Table,
  Tag,
  Typography,
  Skeleton,
  Empty,
} from 'antd';
import {
  FileTextOutlined,
  SendOutlined,
  CheckCircleOutlined,
  UserOutlined,
  RiseOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { statsAPI } from '../../services/api';
import type { DashboardStats, RecentRecord } from '../../utils/types';
import { colors, gradients } from '../../styles/theme';
import PerformanceChart from './PerformanceChart';

const { Text } = Typography;

const statusColorMap: Record<string, string> = {
  success: 'green',
  failed: 'red',
  pending: 'blue',
  running: 'orange',
  cancelled: 'default',
};

const statusTextMap: Record<string, string> = {
  success: '成功',
  failed: '失败',
  pending: '等待中',
  running: '运行中',
  cancelled: '已取消',
};

const StatsPanel: React.FC<{ stats: DashboardStats }> = ({ stats }) => {
  const items = [
    { label: '草稿', value: stats.draft_articles, color: colors.textSecondary, dot: 'inactive' },
    { label: '待执行', value: stats.pending_tasks, color: colors.primary, dot: 'active' },
    { label: '运行中', value: stats.running_tasks, color: colors.warning, dot: 'warning' },
    { label: '成功', value: stats.success_tasks, color: colors.success, dot: 'active' },
    { label: '失败', value: stats.failed_tasks, color: colors.error, dot: 'error' },
  ];

  return (
    <div style={{ padding: '12px 0' }}>
      {items.map((item, index) => (
        <div
          key={index}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px 16px',
            borderRadius: 8,
            marginBottom: 4,
            transition: 'all 0.2s ease',
            cursor: 'default',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = colors.bgHover;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className={`status-dot ${item.dot}`} />
            <Text style={{ color: colors.textSecondary, fontSize: 14 }}>{item.label}</Text>
          </div>
          <Text style={{
            color: item.color,
            fontSize: 20,
            fontWeight: 700,
            fontVariantNumeric: 'tabular-nums',
          }}>
            {item.value}
          </Text>
        </div>
      ))}
    </div>
  );
};

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentRecords, setRecentRecords] = useState<RecentRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const [statsRes, recordsRes] = await Promise.all([
        statsAPI.dashboard(),
        statsAPI.recentRecords(),
      ]);
      setStats(statsRes.data);
      setRecentRecords(recordsRes.data.map((r: RecentRecord, i: number) => ({ ...r, key: String(r.id || i) })));
    } catch {
      setStats({
        total_articles: 0, draft_articles: 0, published_articles: 0,
        total_accounts: 0, active_accounts: 0, logged_in_accounts: 0,
        total_tasks: 0, pending_tasks: 0, running_tasks: 0,
        success_tasks: 0, failed_tasks: 0,
        today_published: 0, today_generated: 0,
      });
      setRecentRecords([]);
    } finally {
      setLoading(false);
    }
  };

  const statCards = stats ? [
    {
      title: '总文章数',
      value: stats.total_articles,
      icon: <FileTextOutlined />,
      color: '#1677ff',
      gradient: gradients.cardBlue,
      accentClass: 'blue',
      suffix: '篇',
    },
    {
      title: '今日发布',
      value: stats.today_published,
      icon: <SendOutlined />,
      color: '#52c41a',
      gradient: gradients.cardGreen,
      accentClass: 'green',
      suffix: '篇',
    },
    {
      title: '发布成功率',
      value: stats.success_tasks + stats.failed_tasks > 0
        ? Math.round((stats.success_tasks / (stats.success_tasks + stats.failed_tasks)) * 100)
        : 100,
      icon: <CheckCircleOutlined />,
      color: '#faad14',
      gradient: gradients.cardYellow,
      accentClass: 'yellow',
      suffix: '%',
    },
    {
      title: '已登录账号',
      value: stats.logged_in_accounts,
      icon: <UserOutlined />,
      color: '#722ed1',
      gradient: gradients.cardPurple,
      accentClass: 'purple',
      suffix: `/ ${stats.total_accounts}`,
    },
  ] : [];

  const columns = [
    {
      title: '文章标题',
      dataIndex: 'article_title',
      key: 'title',
      ellipsis: true,
      render: (text: string) => (
        <Text style={{ color: colors.textPrimary, fontSize: 13 }} ellipsis={{ tooltip: text }}>
          {text}
        </Text>
      ),
    },
    {
      title: '发布账号',
      dataIndex: 'account_nickname',
      key: 'account',
      width: 120,
      render: (text: string) => (
        <Text style={{ color: colors.textSecondary, fontSize: 13 }}>{text}</Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => (
        <Tag color={statusColorMap[status]}>{statusTextMap[status]}</Tag>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'time',
      width: 160,
      render: (time: string) => (
        <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
          <ClockCircleOutlined style={{ marginRight: 6 }} />
          {time ? new Date(time).toLocaleString('zh-CN') : '-'}
        </Text>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="stagger-children">
        <Row gutter={[16, 16]}>
          {[1, 2, 3, 4].map((i) => (
            <Col xs={24} sm={12} lg={6} key={i}>
              <Card
                className="stat-card blue"
                style={{ background: colors.bgContainer, borderColor: colors.border, borderRadius: 12 }}
                styles={{ body: { padding: '20px 24px' } }}
              >
                <Skeleton.Input active size="small" style={{ width: 80, marginBottom: 12 }} />
                <Skeleton.Input active size="large" style={{ width: 120, height: 36 }} />
              </Card>
            </Col>
          ))}
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={10}>
            <Card style={{ background: colors.bgContainer, borderColor: colors.border, borderRadius: 12 }}>
              <Skeleton active paragraph={{ rows: 5 }} />
            </Card>
          </Col>
          <Col xs={24} lg={14}>
            <Card style={{ background: colors.bgContainer, borderColor: colors.border, borderRadius: 12 }}>
              <Skeleton active paragraph={{ rows: 6 }} />
            </Card>
          </Col>
        </Row>
      </div>
    );
  }

  return (
    <div>
      {/* Stat Cards */}
      <Row gutter={[16, 16]} className="stagger-children">
        {statCards.map((card, index) => (
          <Col xs={24} sm={12} lg={6} key={index}>
            <Card
              className={`stat-card ${card.accentClass}`}
              style={{
                background: card.gradient,
                borderColor: colors.border,
                borderRadius: 12,
              }}
              styles={{ body: { padding: '20px 24px' } }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <Text style={{
                    color: colors.textSecondary,
                    fontSize: 13,
                    display: 'block',
                    marginBottom: 8,
                    fontWeight: 500,
                    letterSpacing: '0.3px',
                  }}>
                    {card.title}
                  </Text>
                  <Statistic
                    value={card.value}
                    suffix={<span style={{ fontSize: 13, color: colors.textTertiary, fontWeight: 400 }}>{card.suffix}</span>}
                    valueStyle={{
                      color: card.color,
                      fontSize: 30,
                      fontWeight: 700,
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  />
                </div>
                <div style={{
                  width: 46,
                  height: 46,
                  borderRadius: 12,
                  background: `${card.color}12`,
                  border: `1px solid ${card.color}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 20,
                  color: card.color,
                  transition: 'all 0.3s ease',
                }}>
                  {card.icon}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Bottom Section */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {/* Task Overview */}
        <Col xs={24} lg={10}>
          <Card
            title={
              <span className="section-title">
                <RiseOutlined style={{ marginRight: 8, color: colors.primary }} />
                任务概览
              </span>
            }
            className="card-header-gradient"
            style={{
              background: colors.bgContainer,
              borderColor: colors.border,
              borderRadius: 12,
              height: '100%',
            }}
            styles={{ header: { borderBottom: `1px solid ${colors.border}` } }}
          >
            {stats ? <StatsPanel stats={stats} /> : <Empty description="暂无数据" />}
          </Card>
        </Col>

        {/* Recent Records */}
        <Col xs={24} lg={14}>
          <Card
            title={
              <span className="section-title">
                <ClockCircleOutlined style={{ marginRight: 8, color: colors.primary }} />
                最近发文记录
              </span>
            }
            className="card-header-gradient enhanced-table"
            style={{
              background: colors.bgContainer,
              borderColor: colors.border,
              borderRadius: 12,
              height: '100%',
            }}
            styles={{ header: { borderBottom: `1px solid ${colors.border}` }, body: { padding: 0 } }}
          >
            <Table
              columns={columns}
              dataSource={recentRecords}
              pagination={false}
              size="middle"
            />
          </Card>
        </Col>
      </Row>

      {/* Performance Chart */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <PerformanceChart />
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
