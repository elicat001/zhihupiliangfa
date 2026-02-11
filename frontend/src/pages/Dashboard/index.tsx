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
} from '@ant-design/icons';
import { statsAPI } from '../../services/api';
import type { DashboardStats, RecentRecord } from '../../utils/types';
import PerformanceChart from './PerformanceChart';

const { Title, Text } = Typography;

/** 任务状态颜色映射 */
const statusColorMap: Record<string, string> = {
  success: 'green',
  failed: 'red',
  pending: 'blue',
  running: 'orange',
  cancelled: 'default',
};

/** 任务状态文字映射 */
const statusTextMap: Record<string, string> = {
  success: '成功',
  failed: '失败',
  pending: '等待中',
  running: '运行中',
  cancelled: '已取消',
};

/** 简易统计面板 */
const StatsPanel: React.FC<{ stats: DashboardStats }> = ({ stats }) => {
  const items = [
    { label: '草稿', value: stats.draft_articles, color: '#a0a0a0' },
    { label: '待执行', value: stats.pending_tasks, color: '#1677ff' },
    { label: '运行中', value: stats.running_tasks, color: '#faad14' },
    { label: '成功', value: stats.success_tasks, color: '#52c41a' },
    { label: '失败', value: stats.failed_tasks, color: '#ff4d4f' },
  ];

  return (
    <div style={{ padding: '20px 0' }}>
      {items.map((item, index) => (
        <div
          key={index}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '10px 0',
            borderBottom: index < items.length - 1 ? '1px solid #2a2a3e' : 'none',
          }}
        >
          <Text style={{ color: '#a0a0a0', fontSize: 14 }}>{item.label}</Text>
          <Text style={{ color: item.color, fontSize: 20, fontWeight: 600 }}>
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
      // fallback
      setStats({
        total_articles: 0,
        draft_articles: 0,
        published_articles: 0,
        total_accounts: 0,
        active_accounts: 0,
        logged_in_accounts: 0,
        total_tasks: 0,
        pending_tasks: 0,
        running_tasks: 0,
        success_tasks: 0,
        failed_tasks: 0,
        today_published: 0,
        today_generated: 0,
      });
      setRecentRecords([]);
    } finally {
      setLoading(false);
    }
  };

  /** 统计卡片数据 */
  const statCards = stats
    ? [
        {
          title: '总文章数',
          value: stats.total_articles,
          icon: <FileTextOutlined />,
          color: '#1677ff',
          suffix: '篇',
        },
        {
          title: '今日发布',
          value: stats.today_published,
          icon: <SendOutlined />,
          color: '#52c41a',
          suffix: '篇',
        },
        {
          title: '成功率',
          value:
            stats.success_tasks + stats.failed_tasks > 0
              ? Math.round(
                  (stats.success_tasks /
                    (stats.success_tasks + stats.failed_tasks)) *
                    100
                )
              : 100,
          icon: <CheckCircleOutlined />,
          color: '#faad14',
          suffix: '%',
        },
        {
          title: '已登录账号',
          value: stats.logged_in_accounts,
          icon: <UserOutlined />,
          color: '#722ed1',
          suffix: `/ ${stats.total_accounts}`,
        },
      ]
    : [];

  const columns = [
    {
      title: '文章标题',
      dataIndex: 'article_title',
      key: 'title',
      ellipsis: true,
      render: (text: string) => (
        <Text style={{ color: '#e8e8e8' }} ellipsis={{ tooltip: text }}>
          {text}
        </Text>
      ),
    },
    {
      title: '发布账号',
      dataIndex: 'account_nickname',
      key: 'account',
      width: 130,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusColorMap[status]}>{statusTextMap[status]}</Tag>
      ),
    },
    {
      title: '发布时间',
      dataIndex: 'created_at',
      key: 'time',
      width: 170,
      render: (time: string) => (
        <Text style={{ color: '#a0a0a0', fontSize: 13 }}>
          <ClockCircleOutlined style={{ marginRight: 6 }} />
          {time ? new Date(time).toLocaleString('zh-CN') : '-'}
        </Text>
      ),
    },
  ];

  if (loading) {
    return (
      <div>
        {/* Skeleton for stat cards */}
        <Row gutter={[16, 16]}>
          {[1, 2, 3, 4].map((i) => (
            <Col xs={24} sm={12} lg={6} key={i}>
              <Card
                style={{
                  background: '#1f1f1f',
                  borderColor: '#2a2a3e',
                  borderRadius: 12,
                }}
                bodyStyle={{ padding: '20px 24px' }}
              >
                <Skeleton.Input active size="small" style={{ width: 80, marginBottom: 12 }} />
                <Skeleton.Input active size="large" style={{ width: 120, height: 40 }} />
              </Card>
            </Col>
          ))}
        </Row>

        {/* Skeleton for bottom section */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={10}>
            <Card
              style={{
                background: '#1f1f1f',
                borderColor: '#2a2a3e',
                borderRadius: 12,
              }}
            >
              <Skeleton active paragraph={{ rows: 5 }} />
            </Card>
          </Col>
          <Col xs={24} lg={14}>
            <Card
              style={{
                background: '#1f1f1f',
                borderColor: '#2a2a3e',
                borderRadius: 12,
              }}
            >
              <Skeleton active paragraph={{ rows: 6 }} />
            </Card>
          </Col>
        </Row>
      </div>
    );
  }

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        {statCards.map((card, index) => (
          <Col xs={24} sm={12} lg={6} key={index}>
            <Card
              style={{
                background: '#1f1f1f',
                borderColor: '#2a2a3e',
                borderRadius: 12,
              }}
              bodyStyle={{ padding: '20px 24px' }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                }}
              >
                <div>
                  <Text
                    style={{
                      color: '#a0a0a0',
                      fontSize: 14,
                      display: 'block',
                      marginBottom: 8,
                    }}
                  >
                    {card.title}
                  </Text>
                  <Statistic
                    value={card.value}
                    suffix={
                      <span style={{ fontSize: 14, color: '#a0a0a0' }}>
                        {card.suffix}
                      </span>
                    }
                    valueStyle={{
                      color: card.color,
                      fontSize: 32,
                      fontWeight: 700,
                    }}
                  />
                </div>
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: `${card.color}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 22,
                    color: card.color,
                  }}
                >
                  {card.icon}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 下方区域：趋势图 + 最近记录 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {/* 发文趋势 */}
        <Col xs={24} lg={10}>
          <Card
            title={
              <span style={{ color: '#e8e8e8' }}>
                <RiseOutlined style={{ marginRight: 8, color: '#1677ff' }} />
                任务概览
              </span>
            }
            style={{
              background: '#1f1f1f',
              borderColor: '#2a2a3e',
              borderRadius: 12,
              height: '100%',
            }}
            headStyle={{
              borderBottom: '1px solid #2a2a3e',
              color: '#e8e8e8',
            }}
          >
            {stats ? <StatsPanel stats={stats} /> : <Empty description="暂无数据" />}
          </Card>
        </Col>

        {/* 最近发文记录 */}
        <Col xs={24} lg={14}>
          <Card
            title={
              <span style={{ color: '#e8e8e8' }}>
                <ClockCircleOutlined
                  style={{ marginRight: 8, color: '#1677ff' }}
                />
                最近发文记录
              </span>
            }
            style={{
              background: '#1f1f1f',
              borderColor: '#2a2a3e',
              borderRadius: 12,
              height: '100%',
            }}
            headStyle={{
              borderBottom: '1px solid #2a2a3e',
              color: '#e8e8e8',
            }}
            bodyStyle={{ padding: 0 }}
          >
            <Table
              columns={columns}
              dataSource={recentRecords}
              pagination={false}
              size="middle"
              style={{ background: 'transparent' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 发布效果分析 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <PerformanceChart />
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
