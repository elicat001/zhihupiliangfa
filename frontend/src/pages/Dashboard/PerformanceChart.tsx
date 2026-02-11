import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, Typography, Space, Tag, Table, Empty } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { statsAPI } from '../../services/api';

const { Text, Title } = Typography;

interface HourDistribution {
  hour: number;
  total: number;
  success: number;
  failed: number;
}

const PerformanceChart: React.FC = () => {
  const [distribution, setDistribution] = useState<HourDistribution[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Call the hour-distribution endpoint (GET /api/stats/hour-distribution)
      const res = await statsAPI.hourDistribution();
      setDistribution(res.data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  const totalPublishes = distribution.reduce((sum, d) => sum + d.total, 0);
  const totalSuccess = distribution.reduce((sum, d) => sum + d.success, 0);
  const totalFailed = distribution.reduce((sum, d) => sum + d.failed, 0);
  const successRate = totalPublishes > 0 ? Math.round((totalSuccess / totalPublishes) * 100) : 0;

  // Find peak hour
  const peakHour = distribution.reduce((max, d) => d.total > max.total ? d : max, { hour: 0, total: 0, success: 0, failed: 0 });

  // Filter active hours (those with publishes) for the table
  const activeHours = distribution.filter(d => d.total > 0).sort((a, b) => b.total - a.total);

  const columns = [
    { title: '时段', dataIndex: 'hour', key: 'hour', render: (h: number) => `${String(h).padStart(2, '0')}:00` },
    { title: '总发布', dataIndex: 'total', key: 'total' },
    { title: '成功', dataIndex: 'success', key: 'success', render: (v: number) => <Text style={{ color: '#52c41a' }}>{v}</Text> },
    { title: '失败', dataIndex: 'failed', key: 'failed', render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{v}</Text> },
    {
      title: '成功率', key: 'rate',
      render: (_: any, r: HourDistribution) => {
        const rate = r.total > 0 ? Math.round((r.success / r.total) * 100) : 0;
        return <Progress percent={rate} size="small" strokeColor={rate >= 80 ? '#52c41a' : rate >= 50 ? '#faad14' : '#ff4d4f'} />;
      }
    },
  ];

  return (
    <Card
      title={<span style={{ color: '#e8e8e8' }}><ThunderboltOutlined style={{ marginRight: 8, color: '#1677ff' }} />发布效果分析</span>}
      style={{ background: '#1f1f1f', borderColor: '#2a2a3e', borderRadius: 12 }}
      headStyle={{ borderBottom: '1px solid #2a2a3e' }}
      loading={loading}
    >
      {/* Summary stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card style={{ background: '#141414', borderColor: '#2a2a3e', borderRadius: 8 }} bodyStyle={{ padding: '16px' }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>总发布次数</Text>} value={totalPublishes} valueStyle={{ color: '#1677ff' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ background: '#141414', borderColor: '#2a2a3e', borderRadius: 8 }} bodyStyle={{ padding: '16px' }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>成功次数</Text>} value={totalSuccess} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ background: '#141414', borderColor: '#2a2a3e', borderRadius: 8 }} bodyStyle={{ padding: '16px' }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>失败次数</Text>} value={totalFailed} prefix={<CloseCircleOutlined />} valueStyle={{ color: '#ff4d4f' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ background: '#141414', borderColor: '#2a2a3e', borderRadius: 8 }} bodyStyle={{ padding: '16px' }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>总成功率</Text>} value={successRate} suffix="%" prefix={<ClockCircleOutlined />} valueStyle={{ color: successRate >= 80 ? '#52c41a' : '#faad14' }} />
          </Card>
        </Col>
      </Row>

      {/* Peak hour info */}
      {peakHour.total > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Tag color="blue">高峰时段: {String(peakHour.hour).padStart(2, '0')}:00 ({peakHour.total} 次发布)</Tag>
        </div>
      )}

      {/* Hourly distribution table */}
      {activeHours.length > 0 ? (
        <Table
          columns={columns}
          dataSource={activeHours}
          rowKey="hour"
          size="small"
          pagination={false}
        />
      ) : (
        <Empty description={<Text style={{ color: '#666' }}>暂无发布数据</Text>} />
      )}
    </Card>
  );
};

export default PerformanceChart;
