import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Form,
  Select,
  DatePicker,
  Switch,
  Tag,
  Typography,
  Space,
  Row,
  Col,
  message,
  Divider,
  Popconfirm,
  InputNumber,
  Segmented,
  Tooltip,
  Spin,
} from 'antd';
import {
  ScheduleOutlined,
  PlusOutlined,
  SendOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  CalendarOutlined,
  UnorderedListOutlined,
  StarFilled,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useTaskStore } from '../../stores/taskStore';
import { useArticleStore } from '../../stores/articleStore';
import { useAccountStore } from '../../stores/accountStore';
import { useSSE } from '../../hooks/useSSE';
import { statsAPI } from '../../services/api';
import { colors } from '../../styles/theme';
import Calendar from './Calendar';
import type { PublishTask, TaskStatus } from '../../utils/types';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;

// ---------------------------------------------------------------
// Optimal-time entry returned by the backend
// ---------------------------------------------------------------
interface OptimalTimeEntry {
  hour: number;
  score: number;
  reason: string;
}

/** Task status -> tag colour / label */
const taskStatusConfig: Record<
  TaskStatus,
  { color: string; text: string }
> = {
  pending: { color: 'blue', text: '等待中' },
  running: { color: 'orange', text: '运行中' },
  success: { color: 'green', text: '成功' },
  failed: { color: 'red', text: '失败' },
  cancelled: { color: 'default', text: '已取消' },
};

type ViewMode = '列表视图' | '日历视图';

const TaskSchedule: React.FC = () => {
  const {
    tasks,
    total,
    currentPage,
    pageSize,
    loading,
    publishing,
    fetchTasks,
    publishNow,
    schedulePublish,
    scheduleBatch,
    cancelTask,
  } = useTaskStore();
  const { articles, fetchArticles } = useArticleStore();
  const { accounts, fetchAccounts } = useAccountStore();

  const [form] = Form.useForm();
  const [isBatch, setIsBatch] = useState(false);
  const [isScheduled, setIsScheduled] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [viewMode, setViewMode] = useState<ViewMode>('列表视图');

  // Optimal times state
  const [optimalTimes, setOptimalTimes] = useState<OptimalTimeEntry[]>([]);
  const [optimalLoading, setOptimalLoading] = useState(false);

  // Counter bumped on every SSE refresh so child Calendar can react.
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);

  // ---------------------------------------------------------------
  // SSE real-time updates
  // ---------------------------------------------------------------
  const handleSSEEvent = useCallback(
    (event: { type: string; [key: string]: any }) => {
      if (
        event.type === 'task_update' ||
        event.type === 'task_created'
      ) {
        // Refresh the task list (the current page with current filters).
        fetchTasks({
          page: currentPage,
          page_size: pageSize,
          status: statusFilter as TaskStatus | undefined,
        });
        // Also tell the Calendar to refetch.
        setCalendarRefreshKey((k) => k + 1);
      }
      // Account status changes are handled elsewhere but could be added here.
    },
    [currentPage, pageSize, statusFilter, fetchTasks],
  );

  useSSE({
    enabled: true,
    reconnectDelay: 3000,
    onEvent: handleSSEEvent,
  });

  // ---------------------------------------------------------------
  // Initial data fetch
  // ---------------------------------------------------------------
  useEffect(() => {
    fetchTasks({ page: 1, page_size: 10 });
    fetchArticles({ page: 1, page_size: 100 });
    fetchAccounts();
    fetchOptimalTimes();
  }, []);

  // ---------------------------------------------------------------
  // Fallback polling (30 s) when there are pending / running tasks
  // ---------------------------------------------------------------
  useEffect(() => {
    const hasPendingOrRunning = tasks.some(
      (t) => t.status === 'pending' || t.status === 'running',
    );
    if (!hasPendingOrRunning) return;

    const timer = setInterval(() => {
      fetchTasks({
        page: currentPage,
        page_size: pageSize,
        status: statusFilter as TaskStatus | undefined,
      });
    }, 30000);

    return () => clearInterval(timer);
  }, [tasks, currentPage, pageSize, statusFilter]);

  // ---------------------------------------------------------------
  // Optimal publishing times
  // ---------------------------------------------------------------
  const fetchOptimalTimes = async (accountId?: number) => {
    setOptimalLoading(true);
    try {
      const res = await statsAPI.optimalTimes(accountId, 30);
      setOptimalTimes(res.data ?? []);
    } catch {
      // ignore
    } finally {
      setOptimalLoading(false);
    }
  };

  /** When user clicks an optimal-time chip, fill the scheduled_at picker. */
  const handleOptimalTimeClick = (hour: number) => {
    // Build a dayjs for "today (or tomorrow if hour already passed) at HH:00"
    let target = dayjs().hour(hour).minute(0).second(0);
    if (target.isBefore(dayjs())) {
      target = target.add(1, 'day');
    }

    // Switch form to scheduled mode and fill the DatePicker.
    setIsScheduled(true);
    setIsBatch(false);
    form.setFieldsValue({ scheduledTime: target });
    message.info(`已设置发布时间为 ${target.format('YYYY-MM-DD HH:mm')}`);
  };

  // ---------------------------------------------------------------
  // Create task handler
  // ---------------------------------------------------------------
  const handleCreateTask = async () => {
    try {
      const values = await form.validateFields();

      if (isBatch) {
        await scheduleBatch({
          article_ids: values.articleIds,
          account_id: values.accountId,
          interval_minutes: values.intervalMinutes || 10,
        });
        message.success('批量发布任务已创建');
      } else if (isScheduled && values.scheduledTime) {
        await schedulePublish({
          article_id: values.articleId,
          account_id: values.accountId,
          scheduled_at: values.scheduledTime.toISOString(),
        });
        message.success('定时发布任务已创建');
      } else {
        await publishNow(values.articleId, values.accountId);
        message.success('发布任务已创建');
      }

      form.resetFields();
      fetchTasks({ page: 1, page_size: pageSize });
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('创建任务失败');
    }
  };

  /** Cancel a task */
  const handleCancel = async (id: number) => {
    try {
      await cancelTask(id);
      message.success('任务已取消');
    } catch {
      message.error('取消任务失败');
    }
  };

  /** Pagination */
  const handlePageChange = (page: number, size: number) => {
    fetchTasks({
      page,
      page_size: size,
      status: statusFilter as TaskStatus | undefined,
    });
  };

  /** Status filter */
  const handleStatusFilter = (status: string | undefined) => {
    setStatusFilter(status);
    fetchTasks({
      page: 1,
      page_size: pageSize,
      status: status as TaskStatus | undefined,
    });
  };

  // ---------------------------------------------------------------
  // Select options
  // ---------------------------------------------------------------
  const articleOptions = articles
    .filter((a) => a.status === 'draft' || a.status === 'pending')
    .map((a) => ({
      label: `${a.title} (${a.word_count}字)`,
      value: a.id,
    }));

  const accountOptions = accounts.map((a) => ({
    label: `${a.nickname || '未命名'} ${a.login_status === 'logged_in' ? '(在线)' : '(离线)'}`,
    value: a.id,
  }));

  // ---------------------------------------------------------------
  // Table columns
  // ---------------------------------------------------------------
  const columns: ColumnsType<PublishTask> = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: TaskStatus) => (
        <Tag color={taskStatusConfig[status]?.color}>
          {taskStatusConfig[status]?.text || status}
        </Tag>
      ),
    },
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
      width: 130,
      render: (text: string) => (
        <Text style={{ color: colors.textSecondary }}>{text}</Text>
      ),
    },
    {
      title: '计划时间',
      dataIndex: 'scheduled_at',
      key: 'scheduled_at',
      width: 170,
      render: (time: string | null) =>
        time ? (
          <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {new Date(time).toLocaleString('zh-CN')}
          </Text>
        ) : (
          <Text style={{ color: colors.textTertiary, fontSize: 13 }}>立即执行</Text>
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
      title: '重试',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 60,
      render: (count: number) => (
        <Text style={{ color: count > 0 ? colors.warning : colors.textTertiary }}>{count}</Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: PublishTask) => {
        if (record.status === 'pending' || record.status === 'running') {
          return (
            <Popconfirm
              title="确认取消此任务？"
              onConfirm={() => handleCancel(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<CloseCircleOutlined />}
              >
                取消
              </Button>
            </Popconfirm>
          );
        }
        if (record.status === 'failed') {
          return (
            <Text
              type="danger"
              style={{ fontSize: 12, cursor: 'pointer' }}
              ellipsis={{ tooltip: record.error_message }}
            >
              {record.error_message || '未知错误'}
            </Text>
          );
        }
        if (record.status === 'success') {
          return (
            <Tag color="green" style={{ fontSize: 12 }}>
              发布成功
            </Tag>
          );
        }
        return <Text style={{ color: colors.textTertiary }}>-</Text>;
      },
    },
  ];

  // ---------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------
  return (
    <Row gutter={[16, 16]}>
      {/* ============ Left side: create task form ============ */}
      <Col xs={24} lg={9}>
        <Card
          className="card-header-gradient"
          title={
            <span className="section-title" style={{ color: colors.textPrimary }}>
              <PlusOutlined style={{ marginRight: 8, color: colors.primary }} />
              创建发文任务
            </span>
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
          }}
          styles={{ header: { borderBottom: `1px solid ${colors.border}` } }}
        >
          <Form form={form} layout="vertical" className="enhanced-form">
            {/* Batch mode toggle */}
            <Form.Item label="批量发布">
              <Switch
                checked={isBatch}
                onChange={setIsBatch}
                checkedChildren="开"
                unCheckedChildren="关"
              />
            </Form.Item>

            {isBatch ? (
              <>
                <Form.Item
                  label="选择文章（可多选）"
                  name="articleIds"
                  rules={[{ required: true, message: '请选择文章' }]}
                >
                  <Select
                    mode="multiple"
                    placeholder="选择要发布的文章"
                    options={articleOptions}
                    maxTagCount={3}
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Form.Item
                  label="选择发布账号"
                  name="accountId"
                  rules={[{ required: true, message: '请选择账号' }]}
                >
                  <Select
                    placeholder="选择发布账号"
                    options={accountOptions}
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Form.Item label="每篇间隔（分钟）" name="intervalMinutes" initialValue={10}>
                  <InputNumber
                    min={5}
                    max={1440}
                    placeholder="10"
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </>
            ) : (
              <>
                <Form.Item
                  label="选择文章"
                  name="articleId"
                  rules={[{ required: true, message: '请选择文章' }]}
                >
                  <Select
                    placeholder="选择要发布的文章"
                    options={articleOptions}
                    showSearch
                    optionFilterProp="label"
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Form.Item
                  label="选择发布账号"
                  name="accountId"
                  rules={[{ required: true, message: '请选择账号' }]}
                >
                  <Select
                    placeholder="选择发布账号"
                    options={accountOptions}
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Form.Item label="定时发布">
                  <Switch
                    checked={isScheduled}
                    onChange={setIsScheduled}
                    checkedChildren="定时"
                    unCheckedChildren="立即"
                  />
                </Form.Item>

                {isScheduled && (
                  <Form.Item
                    label="计划发布时间"
                    name="scheduledTime"
                    rules={[{ required: true, message: '请选择发布时间' }]}
                  >
                    <DatePicker
                      showTime
                      format="YYYY-MM-DD HH:mm:ss"
                      placeholder="选择发布时间"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                )}
              </>
            )}

            <Divider style={{ borderColor: colors.border }} />

            <Form.Item>
              <Button
                type="primary"
                icon={<SendOutlined />}
                size="large"
                block
                loading={publishing}
                onClick={handleCreateTask}
                style={{
                  height: 44,
                  borderRadius: 8,
                  fontWeight: 600,
                }}
              >
                {isBatch ? '创建批量任务' : isScheduled ? '创建定时任务' : '立即发布'}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Col>

      {/* ============ Right side: view toggle + optimal times + list/calendar ============ */}
      <Col xs={24} lg={15}>
        {/* ---------- Toolbar: view toggle + optimal times ---------- */}
        <Card
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
            marginBottom: 16,
          }}
          styles={{ body: { padding: '12px 16px' } }}
        >
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            {/* View mode toggle */}
            <Segmented
              value={viewMode}
              onChange={(val) => setViewMode(val as ViewMode)}
              options={[
                {
                  label: (
                    <Space size={4}>
                      <UnorderedListOutlined />
                      <span>列表视图</span>
                    </Space>
                  ),
                  value: '列表视图',
                },
                {
                  label: (
                    <Space size={4}>
                      <CalendarOutlined />
                      <span>日历视图</span>
                    </Space>
                  ),
                  value: '日历视图',
                },
              ]}
            />

            {/* Optimal publishing times */}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <Text style={{ color: colors.textSecondary, fontSize: 13, marginRight: 4 }}>
                <ClockCircleOutlined style={{ marginRight: 4 }} />
                最佳时间:
              </Text>
              {optimalLoading ? (
                <Spin size="small" />
              ) : optimalTimes.length === 0 ? (
                <Text style={{ color: colors.textTertiary, fontSize: 12 }}>暂无数据</Text>
              ) : (
                optimalTimes.slice(0, 5).map((t) => (
                  <Tooltip key={t.hour} title={t.reason}>
                    <Tag
                      color="geekblue"
                      style={{
                        cursor: 'pointer',
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      onClick={() => handleOptimalTimeClick(t.hour)}
                    >
                      {String(t.hour).padStart(2, '0')}:00{' '}
                      <StarFilled style={{ color: '#fadb14', fontSize: 10, marginLeft: 2 }} />
                      {t.score.toFixed(2)}
                    </Tag>
                  </Tooltip>
                ))
              )}
            </div>
          </div>
        </Card>

        {/* ---------- List view ---------- */}
        {viewMode === '列表视图' && (
          <Card
            className="card-header-gradient enhanced-table"
            title={
              <span className="section-title" style={{ color: colors.textPrimary }}>
                <ScheduleOutlined style={{ marginRight: 8, color: colors.primary }} />
                任务列表
              </span>
            }
            extra={
              <Space>
                <Select
                  placeholder="筛选状态"
                  value={statusFilter}
                  onChange={handleStatusFilter}
                  allowClear
                  style={{ width: 120 }}
                  options={[
                    { label: '等待中', value: 'pending' },
                    { label: '运行中', value: 'running' },
                    { label: '成功', value: 'success' },
                    { label: '失败', value: 'failed' },
                    { label: '已取消', value: 'cancelled' },
                  ]}
                />
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() =>
                    fetchTasks({
                      page: 1,
                      page_size: pageSize,
                      status: statusFilter as TaskStatus | undefined,
                    })
                  }
                >
                  刷新
                </Button>
              </Space>
            }
            style={{
              background: colors.bgContainer,
              borderColor: colors.border,
              borderRadius: 12,
            }}
            styles={{
              header: { borderBottom: `1px solid ${colors.border}` },
              body: { padding: 0 },
            }}
          >
            <Table
              columns={columns}
              dataSource={tasks}
              rowKey="id"
              loading={loading}
              pagination={{
                current: currentPage,
                pageSize,
                total,
                showSizeChanger: true,
                showTotal: (t) => `共 ${t} 个任务`,
                onChange: handlePageChange,
              }}
              size="middle"
              scroll={{ x: 900 }}
            />
          </Card>
        )}

        {/* ---------- Calendar view ---------- */}
        {viewMode === '日历视图' && (
          <Card
            className="card-header-gradient"
            title={
              <span className="section-title" style={{ color: colors.textPrimary }}>
                <CalendarOutlined style={{ marginRight: 8, color: colors.primary }} />
                任务日历
              </span>
            }
            style={{
              background: colors.bgContainer,
              borderColor: colors.border,
              borderRadius: 12,
            }}
            styles={{ header: { borderBottom: `1px solid ${colors.border}` } }}
          >
            <Calendar refreshKey={calendarRefreshKey} />
          </Card>
        )}
      </Col>
    </Row>
  );
};

export default TaskSchedule;
