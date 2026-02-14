import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Tag, Space, Modal, Form, Select, Slider, Input,
  Row, Col, Statistic, Progress, Tabs, Tooltip, message, Popconfirm,
  Badge, Checkbox, Empty, Spin, Typography,
} from 'antd';
import {
  QuestionCircleOutlined, SearchOutlined, PlusOutlined, SyncOutlined,
  EditOutlined, SendOutlined, DeleteOutlined, EyeOutlined,
  CheckCircleOutlined, CloseCircleOutlined, FireOutlined,
  StarOutlined, LinkOutlined, RobotOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import { qaAPI, accountAPI } from '../../services/api';
import { colors, gradients } from '../../styles/theme';
import type { ZhihuQuestion, ZhihuAnswer, Account, QAStats } from '../../utils/types';

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

const sourceTagMap: Record<string, { color: string; label: string }> = {
  invited: { color: 'blue', label: '邀请回答' },
  recommended: { color: 'purple', label: '推荐回答' },
  hot: { color: 'red', label: '热榜' },
  topic: { color: 'green', label: '话题' },
  manual: { color: 'default', label: '手动添加' },
};

const statusTagMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'processing', label: '待回答' },
  answered: { color: 'success', label: '已生成' },
  skipped: { color: 'default', label: '已跳过' },
  failed: { color: 'error', label: '失败' },
  draft: { color: 'warning', label: '草稿' },
  publishing: { color: 'processing', label: '发布中' },
  published: { color: 'success', label: '已发布' },
};

const styleOptions = [
  { value: 'professional', label: '专业严谨' },
  { value: 'casual', label: '轻松通俗' },
  { value: 'personal', label: '个人经历' },
  { value: 'detailed', label: '深度分析' },
  { value: 'concise', label: '简洁明了' },
  { value: 'storytelling', label: '故事叙述' },
  { value: 'controversial', label: '观点碰撞' },
];

const QuestionAnswer: React.FC = () => {
  // State
  const [questions, setQuestions] = useState<ZhihuQuestion[]>([]);
  const [answers, setAnswers] = useState<ZhihuAnswer[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [stats, setStats] = useState<QAStats | null>(null);
  const [loading, setLoading] = useState({ questions: false, answers: false, stats: false });
  const [questionTotal, setQuestionTotal] = useState(0);
  const [answerTotal, setAnswerTotal] = useState(0);
  const [questionPage, setQuestionPage] = useState(1);
  const [answerPage, setAnswerPage] = useState(1);
  const [activeTab, setActiveTab] = useState('questions');

  // Filters
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [sourceFilter, setSourceFilter] = useState<string | undefined>();

  // Modals
  const [fetchModalOpen, setFetchModalOpen] = useState(false);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [urlModalOpen, setUrlModalOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<ZhihuQuestion | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<ZhihuAnswer | null>(null);
  const [editContent, setEditContent] = useState('');

  // Action loading states
  const [fetchingQuestions, setFetchingQuestions] = useState(false);
  const [generatingAnswer, setGeneratingAnswer] = useState(false);
  const [publishingAnswer, setPublishingAnswer] = useState(false);
  const [addingUrl, setAddingUrl] = useState(false);

  // Forms
  const [fetchForm] = Form.useForm();
  const [generateForm] = Form.useForm();
  const [urlForm] = Form.useForm();

  // Fetch data
  const fetchQuestions = useCallback(async (page = 1) => {
    setLoading(prev => ({ ...prev, questions: true }));
    try {
      const res = await qaAPI.listQuestions({
        page,
        page_size: 15,
        status: statusFilter,
        source: sourceFilter,
        sort_by: 'score',
      });
      setQuestions(res.data.items);
      setQuestionTotal(res.data.total);
    } catch { /* */ }
    setLoading(prev => ({ ...prev, questions: false }));
  }, [statusFilter, sourceFilter]);

  const fetchAnswers = useCallback(async (page = 1) => {
    setLoading(prev => ({ ...prev, answers: true }));
    try {
      const res = await qaAPI.listAnswers({ page, page_size: 15 });
      setAnswers(res.data.items);
      setAnswerTotal(res.data.total);
    } catch { /* */ }
    setLoading(prev => ({ ...prev, answers: false }));
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await qaAPI.getStats();
      setStats(res.data);
    } catch { /* */ }
  }, []);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await accountAPI.list();
      setAccounts(res.data.items.filter((a: Account) => a.login_status === 'logged_in'));
    } catch { /* */ }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchAccounts();
  }, [fetchStats, fetchAccounts]);

  useEffect(() => {
    if (activeTab === 'questions') {
      fetchQuestions(questionPage);
    } else {
      fetchAnswers(answerPage);
    }
  }, [activeTab, questionPage, answerPage, fetchQuestions, fetchAnswers]);

  // Handlers
  const handleFetchQuestions = async () => {
    try {
      const values = await fetchForm.validateFields();
      setFetchingQuestions(true);
      const res = await qaAPI.fetchQuestions({
        account_id: values.account_id,
        sources: values.sources,
        max_count: values.max_count || 20,
      });
      message.success(`抓取完成：新增 ${res.data.new_questions} 个问题`);
      setFetchModalOpen(false);
      fetchQuestions(1);
      fetchStats();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '抓取失败');
    } finally {
      setFetchingQuestions(false);
    }
  };

  const handleGenerateAnswer = async () => {
    if (!selectedQuestion) return;
    try {
      const values = await generateForm.validateFields();
      setGeneratingAnswer(true);
      await qaAPI.generateAnswer({
        question_id: selectedQuestion.id,
        account_id: values.account_id,
        style: values.style || 'professional',
        word_count: values.word_count || 1000,
        ai_provider: values.ai_provider || undefined,
        anti_ai_level: values.anti_ai_level ?? 3,
      });
      message.success('回答生成成功');
      setGenerateModalOpen(false);
      fetchQuestions(questionPage);
      fetchStats();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '生成失败');
    } finally {
      setGeneratingAnswer(false);
    }
  };

  const handlePublishAnswer = async (answer: ZhihuAnswer) => {
    setPublishingAnswer(true);
    try {
      const res = await qaAPI.publishAnswer(answer.id);
      if (res.data.success) {
        message.success('回答发布成功');
      } else {
        message.error(res.data.message || '发布失败');
      }
      fetchAnswers(answerPage);
      fetchStats();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '发布失败');
    } finally {
      setPublishingAnswer(false);
    }
  };

  const handleSkipQuestion = async (id: number) => {
    try {
      await qaAPI.skipQuestion(id);
      message.success('已跳过');
      fetchQuestions(questionPage);
      fetchStats();
    } catch { message.error('操作失败'); }
  };

  const handleDeleteAnswer = async (id: number) => {
    try {
      await qaAPI.deleteAnswer(id);
      message.success('已删除');
      fetchAnswers(answerPage);
      fetchStats();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '删除失败');
    }
  };

  const handleSaveAnswer = async () => {
    if (!selectedAnswer) return;
    try {
      await qaAPI.updateAnswer(selectedAnswer.id, { content: editContent });
      message.success('保存成功');
      setPreviewModalOpen(false);
      fetchAnswers(answerPage);
    } catch { message.error('保存失败'); }
  };

  const handleAddUrl = async () => {
    try {
      const values = await urlForm.validateFields();
      setAddingUrl(true);
      await qaAPI.addManualQuestion(values.url);
      message.success('问题已添加');
      setUrlModalOpen(false);
      urlForm.resetFields();
      fetchQuestions(1);
      fetchStats();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '添加失败');
    } finally {
      setAddingUrl(false);
    }
  };

  // Question columns
  const questionColumns = [
    {
      title: '问题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title: string, record: ZhihuQuestion) => (
        <a
          href={`https://www.zhihu.com/question/${record.question_id}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: colors.primary, fontSize: 13 }}
        >
          {title}
        </a>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (source: string) => {
        const tag = sourceTagMap[source] || { color: 'default', label: source };
        return <Tag color={tag.color}>{tag.label}</Tag>;
      },
    },
    {
      title: '关注',
      dataIndex: 'follower_count',
      key: 'follower_count',
      width: 80,
      sorter: (a: ZhihuQuestion, b: ZhihuQuestion) => a.follower_count - b.follower_count,
      render: (v: number) => <Text style={{ color: colors.textSecondary }}>{v}</Text>,
    },
    {
      title: '回答数',
      dataIndex: 'answer_count',
      key: 'answer_count',
      width: 80,
      render: (v: number) => (
        <Text style={{ color: v <= 5 ? colors.success : v <= 20 ? colors.warning : colors.textTertiary }}>
          {v}
        </Text>
      ),
    },
    {
      title: '评分',
      dataIndex: 'score',
      key: 'score',
      width: 120,
      sorter: (a: ZhihuQuestion, b: ZhihuQuestion) => a.score - b.score,
      render: (score: number) => (
        <Progress
          percent={score}
          size="small"
          strokeColor={score >= 70 ? colors.success : score >= 40 ? colors.warning : colors.error}
          format={(p) => `${p}`}
        />
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => {
        const tag = statusTagMap[status] || { color: 'default', label: status };
        return <Badge status={tag.color as any} text={<Text style={{ color: colors.textSecondary, fontSize: 12 }}>{tag.label}</Text>} />;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: unknown, record: ZhihuQuestion) => (
        <Space size={4}>
          {record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              icon={<RobotOutlined />}
              style={{ color: colors.primary }}
              onClick={() => {
                setSelectedQuestion(record);
                generateForm.setFieldsValue({
                  style: 'professional',
                  word_count: 1000,
                  anti_ai_level: 3,
                });
                setGenerateModalOpen(true);
              }}
            >
              生成回答
            </Button>
          )}
          {record.status === 'pending' && (
            <Popconfirm
              title="确定跳过此问题？"
              onConfirm={() => handleSkipQuestion(record.id)}
            >
              <Button type="link" size="small" style={{ color: colors.textTertiary }}>
                跳过
              </Button>
            </Popconfirm>
          )}
          {record.status === 'answered' && (
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              style={{ color: colors.success }}
              onClick={() => {
                setActiveTab('answers');
              }}
            >
              查看回答
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // Answer columns
  const answerColumns = [
    {
      title: '问题',
      dataIndex: 'question_title',
      key: 'question_title',
      ellipsis: true,
      render: (title: string, record: ZhihuAnswer) => (
        <a
          href={`https://www.zhihu.com/question/${record.zhihu_question_id}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: colors.primary, fontSize: 13 }}
        >
          {title || `问题 #${record.zhihu_question_id}`}
        </a>
      ),
    },
    {
      title: '字数',
      dataIndex: 'word_count',
      key: 'word_count',
      width: 80,
      render: (v: number) => <Text style={{ color: colors.textSecondary }}>{v}</Text>,
    },
    {
      title: 'AI',
      dataIndex: 'ai_provider',
      key: 'ai_provider',
      width: 90,
      render: (v: string) => <Tag>{v || '-'}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => {
        const tag = statusTagMap[status] || { color: 'default', label: status };
        return <Badge status={tag.color as any} text={<Text style={{ color: colors.textSecondary, fontSize: 12 }}>{tag.label}</Text>} />;
      },
    },
    {
      title: '账号',
      dataIndex: 'account_nickname',
      key: 'account_nickname',
      width: 100,
      render: (v: string) => <Text style={{ color: colors.textSecondary, fontSize: 12 }}>{v || '-'}</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: ZhihuAnswer) => (
        <Space size={4}>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            style={{ color: colors.primary }}
            onClick={() => {
              setSelectedAnswer(record);
              setEditContent(record.content);
              setPreviewModalOpen(true);
            }}
          >
            查看
          </Button>
          {(record.status === 'draft' || record.status === 'failed') && (
            <Popconfirm
              title="确定发布此回答？"
              onConfirm={() => handlePublishAnswer(record)}
            >
              <Button
                type="link"
                size="small"
                icon={<SendOutlined />}
                style={{ color: colors.success }}
                loading={publishingAnswer}
              >
                发布
              </Button>
            </Popconfirm>
          )}
          {record.status === 'published' && record.zhihu_answer_url && (
            <a href={record.zhihu_answer_url} target="_blank" rel="noopener noreferrer">
              <Button type="link" size="small" icon={<LinkOutlined />} style={{ color: colors.accent }}>
                查看
              </Button>
            </a>
          )}
          {record.status !== 'published' && (
            <Popconfirm title="确定删除？" onConfirm={() => handleDeleteAnswer(record.id)}>
              <Button type="link" size="small" icon={<DeleteOutlined />} style={{ color: colors.error }}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // Stat cards
  const statCards = [
    { title: '待回答', value: stats?.pending_questions || 0, color: colors.primary, gradient: gradients.cardBlue, accent: 'blue', icon: <QuestionCircleOutlined /> },
    { title: '已生成', value: stats?.total_answers || 0, color: colors.accent, gradient: gradients.cardPurple, accent: 'purple', icon: <RobotOutlined /> },
    { title: '已发布', value: stats?.published_answers || 0, color: colors.success, gradient: gradients.cardGreen, accent: 'green', icon: <CheckCircleOutlined /> },
    { title: '发布失败', value: stats?.failed_answers || 0, color: colors.error, gradient: gradients.cardRed, accent: 'red', icon: <CloseCircleOutlined /> },
  ];

  return (
    <div>
      {/* Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }} className="stagger-children">
        {statCards.map((card, i) => (
          <Col span={6} key={i}>
            <Card
              className={`stat-card ${card.accent}`}
              style={{ background: card.gradient, borderColor: colors.border, borderRadius: 10 }}
              styles={{ body: { padding: '16px 20px' } }}
            >
              <Statistic
                title={<Text style={{ color: colors.textSecondary, fontSize: 12 }}>{card.title}</Text>}
                value={card.value}
                prefix={card.icon}
                valueStyle={{ color: card.color, fontSize: 24, fontWeight: 700 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Main Card */}
      <Card
        className="card-header-gradient"
        title={
          <span className="section-title">
            <QuestionCircleOutlined style={{ marginRight: 8, color: colors.primary }} />
            知乎问答管理
          </span>
        }
        extra={
          <Space>
            <Button
              icon={<PlusOutlined />}
              size="small"
              onClick={() => setUrlModalOpen(true)}
              style={{ borderColor: colors.border }}
            >
              添加URL
            </Button>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              size="small"
              onClick={() => {
                fetchForm.setFieldsValue({
                  sources: ['invited', 'recommended'],
                  max_count: 20,
                });
                setFetchModalOpen(true);
              }}
            >
              抓取问题
            </Button>
          </Space>
        }
        style={{ background: colors.bgContainer, borderColor: colors.border, borderRadius: 12 }}
        styles={{ header: { borderBottom: `1px solid ${colors.border}` } }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'questions',
              label: (
                <span>
                  <QuestionCircleOutlined style={{ marginRight: 4 }} />
                  问题列表
                  {stats && <Badge count={stats.pending_questions} size="small" offset={[8, -2]} />}
                </span>
              ),
              children: (
                <div>
                  {/* Filters */}
                  <Space style={{ marginBottom: 12 }}>
                    <Select
                      placeholder="来源"
                      allowClear
                      size="small"
                      style={{ width: 120 }}
                      value={sourceFilter}
                      onChange={v => { setSourceFilter(v); setQuestionPage(1); }}
                    >
                      <Option value="invited">邀请回答</Option>
                      <Option value="recommended">推荐回答</Option>
                      <Option value="hot">热榜</Option>
                      <Option value="manual">手动添加</Option>
                    </Select>
                    <Select
                      placeholder="状态"
                      allowClear
                      size="small"
                      style={{ width: 100 }}
                      value={statusFilter}
                      onChange={v => { setStatusFilter(v); setQuestionPage(1); }}
                    >
                      <Option value="pending">待回答</Option>
                      <Option value="answered">已生成</Option>
                      <Option value="skipped">已跳过</Option>
                    </Select>
                    <Button
                      size="small"
                      icon={<SyncOutlined />}
                      onClick={() => fetchQuestions(questionPage)}
                    >
                      刷新
                    </Button>
                  </Space>

                  <div className="enhanced-table">
                    <Table
                      columns={questionColumns}
                      dataSource={questions}
                      rowKey="id"
                      size="small"
                      loading={loading.questions}
                      pagination={{
                        current: questionPage,
                        total: questionTotal,
                        pageSize: 15,
                        showSizeChanger: false,
                        onChange: (p) => setQuestionPage(p),
                        showTotal: (t) => `共 ${t} 个问题`,
                      }}
                    />
                  </div>
                </div>
              ),
            },
            {
              key: 'answers',
              label: (
                <span>
                  <EditOutlined style={{ marginRight: 4 }} />
                  回答管理
                  {stats && stats.total_answers > 0 && <Badge count={stats.total_answers} size="small" offset={[8, -2]} />}
                </span>
              ),
              children: (
                <div className="enhanced-table">
                  <Table
                    columns={answerColumns}
                    dataSource={answers}
                    rowKey="id"
                    size="small"
                    loading={loading.answers}
                    pagination={{
                      current: answerPage,
                      total: answerTotal,
                      pageSize: 15,
                      showSizeChanger: false,
                      onChange: (p) => setAnswerPage(p),
                      showTotal: (t) => `共 ${t} 个回答`,
                    }}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* ===== Fetch Questions Modal ===== */}
      <Modal
        title="抓取知乎问题"
        open={fetchModalOpen}
        onCancel={() => setFetchModalOpen(false)}
        onOk={handleFetchQuestions}
        confirmLoading={fetchingQuestions}
        okText="开始抓取"
      >
        <Form form={fetchForm} layout="vertical" className="enhanced-form">
          <Form.Item label="选择账号" name="account_id" rules={[{ required: true, message: '请选择账号' }]}>
            <Select placeholder="选择已登录的账号">
              {accounts.map(a => (
                <Option key={a.id} value={a.id}>{a.nickname}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="抓取来源" name="sources" rules={[{ required: true, message: '请选择来源' }]}>
            <Checkbox.Group>
              <Checkbox value="invited">邀请回答</Checkbox>
              <Checkbox value="recommended">推荐回答</Checkbox>
              <Checkbox value="hot">热榜问题</Checkbox>
            </Checkbox.Group>
          </Form.Item>
          <Form.Item label="最大数量" name="max_count">
            <Slider min={5} max={50} marks={{ 5: '5', 20: '20', 50: '50' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* ===== Generate Answer Modal ===== */}
      <Modal
        title={`生成回答: ${selectedQuestion?.title?.substring(0, 40) || ''}...`}
        open={generateModalOpen}
        onCancel={() => setGenerateModalOpen(false)}
        onOk={handleGenerateAnswer}
        confirmLoading={generatingAnswer}
        okText="生成回答"
        width={560}
      >
        <Form form={generateForm} layout="vertical" className="enhanced-form">
          <Form.Item label="回答账号" name="account_id" rules={[{ required: true, message: '请选择账号' }]}>
            <Select placeholder="选择回答的账号">
              {accounts.map(a => (
                <Option key={a.id} value={a.id}>{a.nickname}</Option>
              ))}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="回答风格" name="style">
                <Select>
                  {styleOptions.map(o => (
                    <Option key={o.value} value={o.value}>{o.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="AI 提供商" name="ai_provider">
                <Select allowClear placeholder="自动选择">
                  <Option value="openai">OpenAI</Option>
                  <Option value="deepseek">DeepSeek</Option>
                  <Option value="claude">Claude</Option>
                  <Option value="qwen">Qwen</Option>
                  <Option value="zhipu">智谱</Option>
                  <Option value="moonshot">Moonshot</Option>
                  <Option value="doubao">豆包</Option>
                  <Option value="gemini">Gemini</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="目标字数" name="word_count">
            <Slider min={200} max={3000} step={100} marks={{ 200: '200', 1000: '1000', 2000: '2000', 3000: '3000' }} />
          </Form.Item>
          <Form.Item label="反AI检测等级" name="anti_ai_level">
            <Slider min={0} max={3} marks={{ 0: '关闭', 1: '轻度', 2: '中度', 3: '强力' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* ===== Answer Preview/Edit Modal ===== */}
      <Modal
        title="回答预览"
        open={previewModalOpen}
        onCancel={() => setPreviewModalOpen(false)}
        width={720}
        footer={
          selectedAnswer?.status === 'draft' || selectedAnswer?.status === 'failed' ? (
            <Space>
              <Button onClick={() => setPreviewModalOpen(false)}>关闭</Button>
              <Button onClick={handleSaveAnswer}>保存修改</Button>
              <Popconfirm title="确定发布？" onConfirm={() => { if (selectedAnswer) handlePublishAnswer(selectedAnswer); setPreviewModalOpen(false); }}>
                <Button type="primary" icon={<SendOutlined />} loading={publishingAnswer}>
                  发布回答
                </Button>
              </Popconfirm>
            </Space>
          ) : (
            <Button onClick={() => setPreviewModalOpen(false)}>关闭</Button>
          )
        }
      >
        {selectedAnswer && (
          <div>
            <div style={{ marginBottom: 12 }}>
              <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
                问题: {selectedAnswer.question_title || selectedAnswer.zhihu_question_id} |
                字数: {selectedAnswer.word_count} |
                AI: {selectedAnswer.ai_provider || '-'} |
                状态: {statusTagMap[selectedAnswer.status]?.label || selectedAnswer.status}
              </Text>
            </div>
            {selectedAnswer.status === 'draft' || selectedAnswer.status === 'failed' ? (
              <TextArea
                value={editContent}
                onChange={e => setEditContent(e.target.value)}
                rows={18}
                style={{
                  background: colors.bgInput,
                  border: `1px solid ${colors.border}`,
                  color: colors.textPrimary,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 13,
                }}
              />
            ) : (
              <div
                style={{
                  background: colors.bgInput,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 8,
                  padding: 16,
                  maxHeight: 500,
                  overflowY: 'auto',
                  color: colors.textPrimary,
                  lineHeight: 1.8,
                  fontSize: 14,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {selectedAnswer.content}
              </div>
            )}
            {selectedAnswer.publish_error && (
              <div style={{ marginTop: 12, padding: '8px 12px', background: 'rgba(255,77,79,0.08)', borderRadius: 6 }}>
                <Text style={{ color: colors.error, fontSize: 12 }}>
                  <CloseCircleOutlined style={{ marginRight: 4 }} />
                  发布失败: {selectedAnswer.publish_error}
                </Text>
              </div>
            )}
            {selectedAnswer.zhihu_answer_url && (
              <div style={{ marginTop: 12 }}>
                <a href={selectedAnswer.zhihu_answer_url} target="_blank" rel="noopener noreferrer">
                  <Button type="link" icon={<LinkOutlined />} style={{ color: colors.primary, padding: 0 }}>
                    查看已发布的回答
                  </Button>
                </a>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* ===== Add URL Modal ===== */}
      <Modal
        title="手动添加问题"
        open={urlModalOpen}
        onCancel={() => { setUrlModalOpen(false); urlForm.resetFields(); }}
        onOk={handleAddUrl}
        confirmLoading={addingUrl}
        okText="添加"
      >
        <Form form={urlForm} layout="vertical" className="enhanced-form">
          <Form.Item
            label="知乎问题URL"
            name="url"
            rules={[
              { required: true, message: '请输入URL' },
              { pattern: /zhihu\.com\/question\/\d+/, message: '请输入有效的知乎问题URL' },
            ]}
          >
            <Input
              placeholder="https://www.zhihu.com/question/..."
              prefix={<LinkOutlined style={{ color: colors.textTertiary }} />}
              style={{ background: colors.bgInput, borderColor: colors.border }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default QuestionAnswer;
