import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Tag,
  Space,
  message,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Badge,
  Tooltip,
  Slider,
  Divider,
  Typography,
} from 'antd';
import {
  RocketOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { ContentDirection, DirectionFormData, PilotStatus } from '../../utils/types';
import { pilotAPI, accountAPI } from '../../services/api';
import type { Account } from '../../utils/types';

const { TextArea } = Input;
const { Text } = Typography;

const ContentPilot: React.FC = () => {
  const [directions, setDirections] = useState<ContentDirection[]>([]);
  const [pilotStatus, setPilotStatus] = useState<PilotStatus | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [runningIds, setRunningIds] = useState<Set<number>>(new Set());
  const [form] = Form.useForm();

  // 加载数据
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [dirRes, statusRes, accRes] = await Promise.all([
        pilotAPI.listDirections(),
        pilotAPI.getStatus(),
        accountAPI.list(),
      ]);
      setDirections(dirRes.data.items);
      setPilotStatus(statusRes.data);
      setAccounts(accRes.data.items || []);
    } catch (e) {
      console.error('加载失败:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 创建/编辑方向
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      // 处理 keywords：从逗号分隔字符串转数组
      if (typeof values.keywords === 'string') {
        values.keywords = values.keywords
          .split(/[,，、\s]+/)
          .filter((k: string) => k.trim())
          .map((k: string) => k.trim());
      }

      if (editingId) {
        await pilotAPI.updateDirection(editingId, values);
        message.success('更新成功');
      } else {
        await pilotAPI.createDirection(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      form.resetFields();
      setEditingId(null);
      fetchData();
    } catch (e: any) {
      if (e?.errorFields) return; // form validation error
      message.error('操作失败: ' + (e?.response?.data?.detail || e?.message || '未知错误'));
    }
  };

  // 编辑方向
  const handleEdit = (record: ContentDirection) => {
    setEditingId(record.id);
    form.setFieldsValue({
      ...record,
      keywords: (record.keywords || []).join('、'),
    });
    setModalVisible(true);
  };

  // 删除方向
  const handleDelete = async (id: number) => {
    try {
      await pilotAPI.deleteDirection(id);
      message.success('删除成功');
      fetchData();
    } catch (e) {
      message.error('删除失败');
    }
  };

  // 启用/停用
  const handleToggle = async (id: number) => {
    try {
      const res = await pilotAPI.toggleDirection(id);
      message.success(res.data.message);
      fetchData();
    } catch (e) {
      message.error('操作失败');
    }
  };

  // 手动触发
  const handleRun = async (id: number) => {
    setRunningIds((prev) => new Set(prev).add(id));
    try {
      const res = await pilotAPI.runDirection(id);
      const data = res.data as any;
      message.success(
        `生成完成: ${data.articles_generated || 0} 篇文章, ${data.articles_published || 0} 篇入队发布`
      );
      fetchData();
    } catch (e: any) {
      message.error('触发失败: ' + (e?.response?.data?.detail || e?.message || ''));
    } finally {
      setRunningIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  // 触发全部
  const handleRunAll = async () => {
    setLoading(true);
    try {
      await pilotAPI.runAll();
      message.success('所有方向已触发');
      fetchData();
    } catch (e) {
      message.error('触发失败');
    } finally {
      setLoading(false);
    }
  };

  const antiAiLabels: Record<number, { text: string; color: string }> = {
    0: { text: '关闭', color: 'default' },
    1: { text: '轻度', color: 'blue' },
    2: { text: '中度', color: 'orange' },
    3: { text: '强力', color: 'red' },
  };

  const columns = [
    {
      title: '方向名称',
      dataIndex: 'name',
      key: 'name',
      width: 160,
      render: (text: string, record: ContentDirection) => (
        <Space>
          <Text strong style={{ color: '#e8e8e8' }}>{text}</Text>
          {record.is_active && <Badge status="processing" />}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) =>
        active ? (
          <Tag color="green" icon={<PlayCircleOutlined />}>运行中</Tag>
        ) : (
          <Tag color="default" icon={<PauseCircleOutlined />}>已停止</Tag>
        ),
    },
    {
      title: '今日/目标',
      key: 'progress',
      width: 100,
      render: (_: unknown, record: ContentDirection) => (
        <Text style={{ color: '#e8e8e8' }}>
          <span style={{ color: record.today_generated >= record.daily_count ? '#52c41a' : '#1677ff', fontWeight: 600 }}>
            {record.today_generated}
          </span>
          {' / '}
          {record.daily_count}
        </Text>
      ),
    },
    {
      title: '累计',
      dataIndex: 'total_generated',
      key: 'total_generated',
      width: 70,
      render: (v: number) => <Text style={{ color: '#a0a0a0' }}>{v}</Text>,
    },
    {
      title: '模式',
      dataIndex: 'generation_mode',
      key: 'generation_mode',
      width: 80,
      render: (mode: string) => {
        const map: Record<string, string> = { single: '单篇', agent: '智能体', story: '故事' };
        return <Tag>{map[mode] || mode}</Tag>;
      },
    },
    {
      title: '反AI检测',
      dataIndex: 'anti_ai_level',
      key: 'anti_ai_level',
      width: 90,
      render: (level: number) => {
        const info = antiAiLabels[level] || antiAiLabels[0];
        return <Tag color={info.color} icon={<SafetyOutlined />}>{info.text}</Tag>;
      },
    },
    {
      title: '自动发布',
      dataIndex: 'auto_publish',
      key: 'auto_publish',
      width: 80,
      render: (v: boolean) => (v ? <Tag color="cyan">开启</Tag> : <Tag>关闭</Tag>),
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render: (_: unknown, record: ContentDirection) => (
        <Space size="small">
          <Tooltip title={record.is_active ? '停止' : '启动'}>
            <Button
              type={record.is_active ? 'default' : 'primary'}
              size="small"
              icon={record.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={() => handleToggle(record.id)}
            />
          </Tooltip>
          <Tooltip title="手动触发一轮">
            <Button
              size="small"
              icon={<ThunderboltOutlined />}
              loading={runningIds.has(record.id)}
              onClick={() => handleRun(record.id)}
              style={{ color: '#faad14' }}
            />
          </Tooltip>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 状态卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small" style={{ background: '#1f1f1f', borderColor: '#2a2a3e' }}>
            <Statistic
              title={<span style={{ color: '#a0a0a0' }}>自动驾驶</span>}
              value={pilotStatus?.is_running ? '运行中' : '已停止'}
              valueStyle={{ color: pilotStatus?.is_running ? '#52c41a' : '#a0a0a0', fontSize: 18 }}
              prefix={pilotStatus?.is_running ? <SyncOutlined spin /> : <PauseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ background: '#1f1f1f', borderColor: '#2a2a3e' }}>
            <Statistic
              title={<span style={{ color: '#a0a0a0' }}>活跃方向</span>}
              value={pilotStatus?.active_directions || 0}
              suffix={<span style={{ fontSize: 14, color: '#a0a0a0' }}>/ {pilotStatus?.total_directions || 0}</span>}
              valueStyle={{ color: '#1677ff', fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ background: '#1f1f1f', borderColor: '#2a2a3e' }}>
            <Statistic
              title={<span style={{ color: '#a0a0a0' }}>今日已生成</span>}
              value={pilotStatus?.today_total_generated || 0}
              suffix="篇"
              valueStyle={{ color: '#faad14', fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ background: '#1f1f1f', borderColor: '#2a2a3e' }}>
            <Statistic
              title={<span style={{ color: '#a0a0a0' }}>调度频率</span>}
              value="每30分钟"
              valueStyle={{ color: '#e8e8e8', fontSize: 18 }}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 方向列表 */}
      <Card
        title={
          <span style={{ color: '#e8e8e8' }}>
            <RocketOutlined style={{ marginRight: 8, color: '#1677ff' }} />
            内容方向管理
          </span>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
            <Button type="primary" ghost onClick={handleRunAll} loading={loading}>
              触发全部
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingId(null);
                form.resetFields();
                form.setFieldsValue({
                  generation_mode: 'single',
                  style: 'professional',
                  word_count: 1500,
                  daily_count: 24,
                  auto_publish: true,
                  publish_interval: 30,
                  anti_ai_level: 3,
                });
                setModalVisible(true);
              }}
            >
              新建方向
            </Button>
          </Space>
        }
        style={{ background: '#1f1f1f', borderColor: '#2a2a3e', borderRadius: 12 }}
        headStyle={{ borderBottom: '1px solid #2a2a3e' }}
      >
        <Table
          dataSource={directions}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="middle"
          locale={{ emptyText: '暂无内容方向，点击"新建方向"开始配置' }}
        />
      </Card>

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editingId ? '编辑内容方向' : '新建内容方向'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingId(null);
          form.resetFields();
        }}
        width={640}
        okText={editingId ? '保存' : '创建'}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="方向名称"
            rules={[{ required: true, message: '请输入方向名称' }]}
          >
            <Input placeholder="如：Python 教程、职场心理学、投资理财" />
          </Form.Item>

          <Form.Item name="description" label="方向描述">
            <TextArea rows={2} placeholder="描述这个内容方向的主题范围和目标受众" />
          </Form.Item>

          <Form.Item
            name="keywords"
            label="核心关键词"
            tooltip="用逗号、顿号或空格分隔"
          >
            <Input placeholder="如：Python、编程入门、后端开发、Django" />
          </Form.Item>

          <Form.Item name="seed_text" label="参考素材（可选）" tooltip="提供参考文章内容，AI将基于此分析生成方向">
            <TextArea rows={3} placeholder="粘贴参考文章内容，用于 AI 分析写作方向..." />
          </Form.Item>

          <Divider style={{ margin: '12px 0', borderColor: '#2a2a3e' }} />

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="generation_mode" label="生成模式">
                <Select>
                  <Select.Option value="single">单篇生成</Select.Option>
                  <Select.Option value="agent">智能体 (Agent)</Select.Option>
                  <Select.Option value="story">故事模式</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="style" label="写作风格">
                <Select>
                  <Select.Option value="professional">专业严谨</Select.Option>
                  <Select.Option value="casual">轻松活泼</Select.Option>
                  <Select.Option value="humorous">幽默风趣</Select.Option>
                  <Select.Option value="storytelling">叙事型</Select.Option>
                  <Select.Option value="tutorial">教程型</Select.Option>
                  <Select.Option value="controversial">观点碰撞型</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="ai_provider" label="AI 提供商">
                <Select allowClear placeholder="自动选择">
                  <Select.Option value="gemini">Gemini</Select.Option>
                  <Select.Option value="codex">GPT-5 Codex</Select.Option>
                  <Select.Option value="openai">OpenAI</Select.Option>
                  <Select.Option value="claude">Claude</Select.Option>
                  <Select.Option value="deepseek">DeepSeek</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="word_count" label="目标字数">
                <InputNumber min={500} max={10000} step={500} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="daily_count" label="每日生成数">
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="publish_interval" label="发布间隔（分钟）">
                <InputNumber min={5} max={240} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider style={{ margin: '12px 0', borderColor: '#2a2a3e' }} />

          <Form.Item
            name="anti_ai_level"
            label={
              <Space>
                <SafetyOutlined />
                反AI检测强度
              </Space>
            }
          >
            <Slider
              min={0}
              max={3}
              marks={{
                0: '关闭',
                1: '轻度',
                2: '中度',
                3: '强力',
              }}
              tooltip={{
                formatter: (v) => {
                  const labels: Record<number, string> = {
                    0: '不做反检测处理',
                    1: '基础去AI味（避免常见套话）',
                    2: '中度去AI味（增加口语化+案例）',
                    3: '强力反检测（全面拟人化写作）',
                  };
                  return labels[v ?? 3];
                },
              }}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="auto_publish" label="自动发布" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="publish_account_id" label="发布账号">
                <Select allowClear placeholder="自动选择（首个已登录账号）">
                  {accounts.map((acc) => (
                    <Select.Option key={acc.id} value={acc.id}>
                      {acc.nickname} {acc.login_status === 'logged_in' ? '(已登录)' : '(未登录)'}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default ContentPilot;
