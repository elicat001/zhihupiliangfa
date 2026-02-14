import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, Typography, Tag, Table, Empty } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { statsAPI } from '../../services/api';
import { colors, gradients } from '../../styles/theme';

const { Text } = Typography;

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
  const peakHour = distribution.reduce((max, d) => d.total > max.total ? d : max, { hour: 0, total: 0, success: 0, failed: 0 });
  const activeHours = distribution.filter(d => d.total > 0).sort((a, b) => b.total - a.total);

  const summaryCards = [
    { title: '总发布', value: totalPublishes, color: colors.primary, gradient: gradients.cardBlue, accentClass: 'blue' },
    { title: '成功', value: totalSuccess, color: colors.success, gradient: gradients.cardGreen, accentClass: 'green', icon: <CheckCircleOutlined /> },
    { title: '失败', value: totalFailed, color: colors.error, gradient: gradients.cardRed, accentClass: 'red', icon: <CloseCircleOutlined /> },
    { title: '成功率', value: successRate, color: successRate >= 80 ? colors.success : colors.warning, gradient: successRate >= 80 ? gradients.cardGreen : gradients.cardYellow, accentClass: successRate >= 80 ? 'green' : 'yellow', suffix: '%', icon: <ClockCircleOutlined /> },
  ];

  const columns = [
    {
      title: '时段',
      dataIndex: 'hour',
      key: 'hour',
      width: 80,
      render: (h: number) => (
        <Text style={{ color: colors.textPrimary, fontVariantNumeric: 'tabular-nums' }}>
          {String(h).padStart(2, '0')}:00
        </Text>
      ),
    },
    { title: '总发布', dataIndex: 'total', key: 'total', width: 80 },
    {
      title: '成功',
      dataIndex: 'success',
      key: 'success',
      width: 80,
      render: (v: number) => <Text style={{ color: colors.success }}>{v}</Text>,
    },
    {
      title: '失败',
      dataIndex: 'failed',
      key: 'failed',
      width: 80,
      render: (v: number) => <Text style={{ color: v > 0 ? colors.error : colors.textTertiary }}>{v}</Text>,
    },
    {
      title: '成功率',
      key: 'rate',
      render: (_: unknown, r: HourDistribution) => {
        const rate = r.total > 0 ? Math.round((r.success / r.total) * 100) : 0;
        return (
          <Progress
            percent={rate}
            size="small"
            strokeColor={rate >= 80 ? colors.success : rate >= 50 ? colors.warning : colors.error}
          />
        );
      },
    },
  ];

  return (
    <Card
      title={
        <span className="section-title">
          <ThunderboltOutlined style={{ marginRight: 8, color: colors.primary }} />
          发布效果分析
        </span>
      }
      className="card-header-gradient"
      style={{ background: colors.bgContainer, borderColor: colors.border, borderRadius: 12 }}
      styles={{ header: { borderBottom: `1px solid ${colors.border}` } }}
      loading={loading}
    >
      {/* Summary */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {summaryCards.map((card, i) => (
          <Col span={6} key={i}>
            <Card
              className={`stat-card ${card.accentClass}`}
              style={{ background: card.gradient, borderColor: colors.border, borderRadius: 8 }}
              styles={{ body: { padding: '14px 16px' } }}
            >
              <Statistic
                title={<Text style={{ color: colors.textSecondary, fontSize: 12 }}>{card.title}</Text>}
                value={card.value}
                suffix={card.suffix}
                prefix={card.icon}
                valueStyle={{ color: card.color, fontSize: 20, fontWeight: 700 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {peakHour.total > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Tag color="blue" style={{ borderRadius: 4 }}>
            <ThunderboltOutlined style={{ marginRight: 4 }} />
            高峰时段: {String(peakHour.hour).padStart(2, '0')}:00 ({peakHour.total} 次)
          </Tag>
        </div>
      )}

      {activeHours.length > 0 ? (
        <div className="enhanced-table">
          <Table
            columns={columns}
            dataSource={activeHours}
            rowKey="hour"
            size="small"
            pagination={false}
          />
        </div>
      ) : (
        <Empty description={<Text style={{ color: colors.textTertiary }}>暂无发布数据</Text>} />
      )}
    </Card>
  );
};

export default PerformanceChart;
