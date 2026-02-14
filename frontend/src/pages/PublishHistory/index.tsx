import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Typography,
  Select,
  DatePicker,
  Space,
  Button,
  Row,
  Col,
  Modal,
  Image,
  message,
} from 'antd';
import {
  HistoryOutlined,
  SearchOutlined,
  ReloadOutlined,
  LinkOutlined,
  PictureOutlined,
  FilterOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { taskAPI } from '../../services/api';
import { useAccountStore } from '../../stores/accountStore';
import { colors } from '../../styles/theme';
import type { PublishTask, TaskStatus } from '../../utils/types';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;
const { RangePicker } = DatePicker;

/** 任务状态配置 */
const statusConfig: Record<TaskStatus, { color: string; text: string }> = {
  pending: { color: 'blue', text: '等待中' },
  running: { color: 'orange', text: '运行中' },
  success: { color: 'green', text: '成功' },
  failed: { color: 'red', text: '失败' },
  cancelled: { color: 'default', text: '已取消' },
};

const PublishHistory: React.FC = () => {
  const { accounts, fetchAccounts } = useAccountStore();

  const [records, setRecords] = useState<PublishTask[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [loading, setLoading] = useState(false);

  // 筛选条件
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [accountFilter, setAccountFilter] = useState<number | undefined>(undefined);
  const [dateRange, setDateRange] = useState<any>(null);

  // 截图弹窗
  const [screenshotVisible, setScreenshotVisible] = useState(false);
  const [screenshotUrl, setScreenshotUrl] = useState('');

  useEffect(() => {
    fetchAccounts();
    fetchHistory(1, 10);
  }, []);

  /** 获取发布历史（复用任务列表API，筛选已完成的） */
  const fetchHistory = async (
    p: number = page,
    ps: number = pageSize,
    filters?: {
      status?: string;
      account_id?: number;
      start_date?: string;
      end_date?: string;
    }
  ) => {
    setLoading(true);
    try {
      const response = await taskAPI.list({
        page: p,
        page_size: ps,
        status: (filters?.status || statusFilter) as TaskStatus | undefined,
        account_id: filters?.account_id ?? accountFilter,
        start_date: filters?.start_date,
        end_date: filters?.end_date,
      });
      const data = response.data;
      setRecords(data.items || []);
      setTotal(data.total || 0);
      setPage(p);
      setPageSize(ps);
    } catch {
      message.error('获取发布历史失败');
    } finally {
      setLoading(false);
    }
  };

  /** 搜索/筛选 */
  const handleFilter = () => {
    const start_date = dateRange?.[0]?.format('YYYY-MM-DD');
    const end_date = dateRange?.[1]?.format('YYYY-MM-DD');
    fetchHistory(1, pageSize, {
      status: statusFilter,
      account_id: accountFilter,
      start_date,
      end_date,
    });
  };

  /** 重置筛选 */
  const handleReset = () => {
    setStatusFilter(undefined);
    setAccountFilter(undefined);
    setDateRange(null);
    fetchHistory(1, 10, { status: undefined, account_id: undefined });
  };

  /** 导出CSV */
  const [exportLoading, setExportLoading] = useState(false);
  const handleExport = async () => {
    setExportLoading(true);
    try {
      const start_date = dateRange?.[0]?.format('YYYY-MM-DD');
      const end_date = dateRange?.[1]?.format('YYYY-MM-DD');
      const response = await taskAPI.exportCSV({
        status: statusFilter,
        account_id: accountFilter,
        start_date,
        end_date,
      });
      // Create download link from blob
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `tasks_export_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    } finally {
      setExportLoading(false);
    }
  };

  /** 查看截图 */
  const handleViewScreenshot = (taskId: number) => {
    // 截图URL - 实际项目中从后端获取
    const url = `/api/tasks/${taskId}/screenshot`;
    setScreenshotUrl(url);
    setScreenshotVisible(true);
  };

  /** 账号选项 */
  const accountOptions = accounts.map((a) => ({
    label: a.nickname || '未命名',
    value: a.id,
  }));

  /** 表格列定义 */
  const columns: ColumnsType<PublishTask> = [
    {
      title: '文章标题',
      dataIndex: 'article_title',
      key: 'article_title',
      ellipsis: true,
      render: (text: string) => (
        <Text style={{ color: colors.textPrimary }} ellipsis={{ tooltip: text }}>
          {text}
        </Text>
      ),
    },
    {
      title: '发布账号',
      dataIndex: 'account_nickname',
      key: 'account_nickname',
      width: 120,
      render: (text: string) => (
        <Text style={{ color: colors.textSecondary }}>{text}</Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: TaskStatus) => (
        <Tag color={statusConfig[status]?.color}>
          {statusConfig[status]?.text || status}
        </Tag>
      ),
    },
    {
      title: '重试次数',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 80,
      render: (count: number) => (
        <Text style={{ color: count > 0 ? colors.warning : colors.textTertiary }}>{count}</Text>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => (
        <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
          {time ? new Date(time).toLocaleString('zh-CN') : '-'}
        </Text>
      ),
    },
    {
      title: '截图',
      key: 'screenshot',
      width: 80,
      render: (_: any, record: PublishTask) =>
        record.status === 'success' ? (
          <Button
            type="text"
            size="small"
            icon={<PictureOutlined />}
            onClick={() => handleViewScreenshot(record.id)}
            style={{ color: colors.primary }}
          >
            查看
          </Button>
        ) : (
          <Text style={{ color: colors.textTertiary }}>-</Text>
        ),
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      width: 150,
      ellipsis: true,
      render: (msg: string | null) =>
        msg ? (
          <Text type="danger" ellipsis={{ tooltip: msg }} style={{ fontSize: 12 }}>
            {msg}
          </Text>
        ) : (
          <Text style={{ color: colors.textTertiary }}>-</Text>
        ),
    },
  ];

  return (
    <div>
      <Card
        className="card-header-gradient enhanced-table"
        title={
          <span className="section-title" style={{ color: colors.textPrimary }}>
            <HistoryOutlined style={{ marginRight: 8, color: colors.primary }} />
            发布历史
          </span>
        }
        style={{
          background: colors.bgContainer,
          borderColor: colors.border,
          borderRadius: 12,
        }}
        styles={{ header: { borderBottom: `1px solid ${colors.border}` } }}
      >
        {/* 筛选栏 */}
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={6}>
            <Select
              placeholder="按状态筛选"
              value={statusFilter}
              onChange={setStatusFilter}
              allowClear
              style={{ width: '100%' }}
              options={[
                { label: '成功', value: 'success' },
                { label: '失败', value: 'failed' },
                { label: '等待中', value: 'pending' },
                { label: '运行中', value: 'running' },
                { label: '已取消', value: 'cancelled' },
              ]}
            />
          </Col>
          <Col xs={24} sm={6}>
            <Select
              placeholder="按账号筛选"
              value={accountFilter}
              onChange={setAccountFilter}
              allowClear
              style={{ width: '100%' }}
              options={accountOptions}
            />
          </Col>
          <Col xs={24} sm={6}>
            <RangePicker
              value={dateRange}
              onChange={setDateRange}
              style={{ width: '100%' }}
              placeholder={['开始日期', '结束日期']}
            />
          </Col>
          <Col xs={24} sm={6}>
            <Space>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleFilter}
              >
                筛选
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                loading={exportLoading}
              >
                导出
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 历史记录表格 */}
        <Table
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条记录`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
              fetchHistory(p, ps);
            },
          }}
          size="middle"
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* 截图查看弹窗 */}
      <Modal
        title="发布截图"
        open={screenshotVisible}
        onCancel={() => setScreenshotVisible(false)}
        footer={null}
        width={800}
      >
        <div
          style={{
            textAlign: 'center',
            padding: 16,
            background: colors.bgInput,
            borderRadius: 8,
            minHeight: 300,
          }}
        >
          <Image
            src={screenshotUrl}
            alt="发布截图"
            style={{ maxWidth: '100%', borderRadius: 4 }}
            fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzFmMWYxZiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE0IiBmaWxsPSIjNjY2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+5peg5oiq5Zu+PC90ZXh0Pjwvc3ZnPg=="
          />
          <div style={{ marginTop: 12, color: colors.textTertiary }}>
            <Text type="secondary">
              截图可能需要几秒钟加载，如无截图则表示发布时未启用截图功能
            </Text>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default PublishHistory;
