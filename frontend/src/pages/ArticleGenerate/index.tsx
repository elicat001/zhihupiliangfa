import React, { useState, useRef, useCallback } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Row,
  Col,
  Typography,
  Tag,
  Divider,
  Space,
  message,
  Spin,
  Empty,
  Modal,
  Tabs,
  Progress,
  List,
  Steps,
  Alert,
  Switch,
} from 'antd';
import {
  RobotOutlined,
  SaveOutlined,
  SendOutlined,
  ReloadOutlined,
  CopyOutlined,
  TagsOutlined,
  FileTextOutlined,
  OrderedListOutlined,
  EditOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  PictureOutlined,
} from '@ant-design/icons';
import { colors } from '../../styles/theme';
import { useArticleStore } from '../../stores/articleStore';
import { useAccountStore } from '../../stores/accountStore';
import { articleAPI, publishAPI, templateAPI, API_BASE_URL } from '../../services/api';
import type {
  GenerateParams,
  GeneratedArticle,
  PromptTemplate,
  SeriesOutlineResponse,
  SeriesOutlineArticle,
  Article,
  AgentGenerateParams,
  StoryGenerateParams,
} from '../../utils/types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

/** AI 提供商选项（需与后端支持的提供商一致） */
const providerOptions = [
  { label: 'Google Gemini', value: 'gemini' },
  { label: 'GPT-5 Codex', value: 'codex' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'OpenAI (GPT-5)', value: 'openai' },
  { label: 'Claude', value: 'claude' },
  { label: '通义千问 (Qwen)', value: 'qwen' },
  { label: '智谱 GLM', value: 'zhipu' },
  { label: '月之暗面 Kimi', value: 'moonshot' },
  { label: '豆包 (Doubao)', value: 'doubao' },
];

/** 文章风格选项 */
const styleOptions = [
  { label: '专业严谨', value: 'professional' },
  { label: '轻松活泼', value: 'casual' },
  { label: '幽默风趣', value: 'humorous' },
  { label: '学术论文', value: 'academic' },
];

/** 字数选项 */
const wordCountOptions = [
  { label: '短文 (500字)', value: 500 },
  { label: '中等 (1000字)', value: 1000 },
  { label: '长文 (1500字)', value: 1500 },
  { label: '深度 (2000字)', value: 2000 },
  { label: '超长 (3000字)', value: 3000 },
];

/** 简易Markdown渲染 - 把基础的标记转换为HTML */
const renderMarkdown = (text: string): string => {
  if (!text) return '';
  let html = text
    // 图片 ![alt](url) → <figure><img></figure>
    .replace(
      /!\[([^\]]*)\]\(([^)]+)\)/g,
      '<figure style="text-align:center;margin:16px 0">'
      + '<img src="$2" alt="$1" style="max-width:100%;border-radius:8px">'
      + '<figcaption style="color:#999;font-size:13px;margin-top:6px">$1</figcaption>'
      + '</figure>'
    )
    // 标题
    .replace(/^### (.+)$/gm, '<h3 style="color:#e8e8e8;margin:16px 0 8px">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 style="color:#e8e8e8;margin:20px 0 10px">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 style="color:#e8e8e8;margin:24px 0 12px">$1</h1>')
    // 加粗
    .replace(/\*\*(.+?)\*\*/g, '<strong style="color:#e8e8e8">$1</strong>')
    // 斜体
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 代码块
    .replace(/```[\s\S]*?```/g, (match) => {
      const code = match.replace(/```\w*\n?/, '').replace(/\n?```$/, '');
      return `<pre style="background:#141414;padding:12px;border-radius:6px;overflow-x:auto;margin:12px 0"><code style="color:#69b1ff">${code}</code></pre>`;
    })
    // 行内代码
    .replace(/`(.+?)`/g, '<code style="background:#141414;padding:2px 6px;border-radius:3px;color:#69b1ff">$1</code>')
    // 无序列表
    .replace(/^- (.+)$/gm, '<li style="margin:4px 0;margin-left:20px">$1</li>')
    // 段落（双换行）
    .replace(/\n\n/g, '</p><p style="margin:8px 0;line-height:1.8">')
    // 单换行
    .replace(/\n/g, '<br/>');
  return `<p style="margin:8px 0;line-height:1.8">${html}</p>`;
};

/** CSS keyframe animation for pulsing cursor (injected once) */
const cursorStyleId = 'streaming-cursor-style';
if (typeof document !== 'undefined' && !document.getElementById(cursorStyleId)) {
  const style = document.createElement('style');
  style.id = cursorStyleId;
  style.textContent = `
    @keyframes streamingCursorBlink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0; }
    }
  `;
  document.head.appendChild(style);
}

const ArticleGenerate: React.FC = () => {
  const [form] = Form.useForm();
  const { generatedArticle, saveArticle, clearGenerated } =
    useArticleStore();
  const [saving, setSaving] = useState(false);
  const { accounts, fetchAccounts: loadAccounts } = useAccountStore();
  const [publishModalVisible, setPublishModalVisible] = useState(false);
  const [publishAccountId, setPublishAccountId] = useState<number | undefined>(undefined);
  const [publishLoading, setPublishLoading] = useState(false);

  // ---- 流式生成相关状态 ----
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const abortControllerRef = useRef<AbortController | null>(null);

  // ---- 内容模板相关状态 ----
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | undefined>(undefined);

  // ---- 系列文章生成相关状态 ----
  const [activeTab, setActiveTab] = useState<string>('single');
  const [seriesForm] = Form.useForm();
  const [seriesOutline, setSeriesOutline] = useState<SeriesOutlineResponse | null>(null);
  const [seriesOutlineLoading, setSeriesOutlineLoading] = useState(false);
  const [seriesGenerating, setSeriesGenerating] = useState(false);
  const [seriesProgress, setSeriesProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 });
  const [seriesArticles, setSeriesArticles] = useState<Article[]>([]);

  // ---- 智能体生成相关状态 ----
  const [agentForm] = Form.useForm();
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentArticles, setAgentArticles] = useState<Article[]>([]);
  const [agentSourceArticles, setAgentSourceArticles] = useState<Article[]>([]);
  const [agentSourceLoading, setAgentSourceLoading] = useState(false);

  // ---- 故事生成相关状态 ----
  const [storyForm] = Form.useForm();
  const [storyLoading, setStoryLoading] = useState(false);
  const [storyArticles, setStoryArticles] = useState<Article[]>([]);
  const [storyPhase, setStoryPhase] = useState<number>(0);

  /** 加载已有文章列表（用于智能体选择参考文章） */
  const loadSourceArticles = async () => {
    setAgentSourceLoading(true);
    try {
      const res = await articleAPI.list({ page: 1, page_size: 100 });
      setAgentSourceArticles(res.data.items || []);
    } catch {
      // 静默
    } finally {
      setAgentSourceLoading(false);
    }
  };

  /** 智能体生成 */
  const handleAgentGenerate = async () => {
    try {
      const values = await agentForm.validateFields();
      setAgentLoading(true);
      setAgentArticles([]);

      const res = await articleAPI.agentGenerate({
        article_ids: values.articleIds,
        count: values.agentCount,
        style: values.agentStyle || undefined,
        word_count: values.agentWordCount,
        ai_provider: values.agentProvider,
      });

      const articles = res.data ?? [];
      setAgentArticles(articles);
      message.success(`智能体成功生成 ${articles.length} 篇文章！`);
    } catch (error: any) {
      if (error?.errorFields) return;
      const detail = error?.response?.data?.detail;
      message.error(detail || '智能体生成失败，请重试');
    } finally {
      setAgentLoading(false);
    }
  };

  /** 故事生成 */
  const handleStoryGenerate = async () => {
    try {
      const values = await storyForm.validateFields();
      setStoryLoading(true);
      setStoryArticles([]);
      setStoryPhase(0);

      // 模拟阶段进度（后端不支持流式阶段推送）
      const phaseInterval = setInterval(() => {
        setStoryPhase((prev) => (prev < 4 ? prev + 1 : prev));
      }, 40000);

      const res = await articleAPI.storyGenerate({
        reference_text: values.referenceText,
        reference_article_ids: values.storyArticleIds || undefined,
        chapter_count: values.chapterCount,
        total_word_count: values.totalWordCount,
        story_type: values.storyType,
        ai_provider: values.storyProvider,
      });

      clearInterval(phaseInterval);
      setStoryPhase(5);

      const articles = res.data ?? [];
      setStoryArticles(articles);
      message.success(`故事生成完成！共 ${articles.length} 篇已保存`);
    } catch (error: any) {
      if (error?.errorFields) return;
      const detail = error?.response?.data?.detail;
      message.error(detail || '故事生成失败，请重试');
    } finally {
      setStoryLoading(false);
    }
  };

  /** 加载模板列表 */
  const loadTemplates = async () => {
    try {
      const res = await templateAPI.list();
      setTemplates(res.data);
    } catch {
      // 静默失败，模板功能为可选
    }
  };

  /** 选择模板后填充默认值 */
  const handleTemplateChange = (templateId: number | undefined) => {
    setSelectedTemplateId(templateId);
    if (!templateId) return;
    const tpl = templates.find((t) => t.id === templateId);
    if (tpl) {
      form.setFieldsValue({
        style: tpl.default_style,
        wordCount: tpl.default_word_count,
      });
    }
  };

  React.useEffect(() => {
    loadAccounts();
    loadTemplates();
    loadSourceArticles();
  }, []);

  /** 流式生成文章 */
  const handleGenerate = useCallback(async () => {
    try {
      const values = await form.validateFields();
      const params: GenerateParams = {
        topic: values.topic,
        style: values.style,
        word_count: values.wordCount,
        ai_provider: values.provider,
        enable_images: values.enableImages || false,
      };

      // 清除之前的生成结果
      clearGenerated();
      setStreamingContent('');
      setIsStreaming(true);

      // 创建 AbortController 以便在需要时中断流
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const response = await fetch(`${API_BASE_URL}/articles/generate-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: 流式生成请求失败`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 按 SSE 协议分割事件（以双换行分隔）
        const parts = buffer.split('\n\n');
        // 最后一个 part 可能是不完整的，留在 buffer 里
        buffer = parts.pop() || '';

        for (const part of parts) {
          const trimmed = part.trim();
          if (!trimmed.startsWith('data: ')) continue;

          const jsonStr = trimmed.slice(6); // 去掉 "data: "
          try {
            const event = JSON.parse(jsonStr);

            if (event.type === 'content') {
              // 增量追加内容
              setStreamingContent((prev) => prev + event.text);
            } else if (event.type === 'done') {
              // 生成完毕，设置最终文章数据
              const article = event.article as GeneratedArticle;
              useArticleStore.setState({ generatedArticle: article });
              setIsStreaming(false);
              setStreamingContent('');
              message.success('文章生成成功！');
            } else if (event.type === 'error') {
              setIsStreaming(false);
              message.error(event.message || '文章生成失败');
            }
          } catch {
            // 忽略解析错误的事件
          }
        }
      }

      // 如果循环结束但还没收到 done 事件
      setIsStreaming(false);
    } catch (error: any) {
      if (error?.errorFields) return; // 表单验证失败
      if (error?.name === 'AbortError') {
        message.info('已取消生成');
      } else {
        message.error('文章生成失败，请重试');
      }
      setIsStreaming(false);
    }
  }, [form, clearGenerated]);

  /** 保存为草稿 */
  const handleSaveDraft = async () => {
    if (!generatedArticle) return;
    setSaving(true);
    try {
      await saveArticle({
        title: generatedArticle.title,
        content: generatedArticle.content,
        tags: generatedArticle.tags,
        summary: generatedArticle.summary,
      });
      message.success('草稿保存成功！');
      clearGenerated();
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  /** 直接发布 - 先保存，再选账号发布 */
  const handlePublish = async () => {
    if (!generatedArticle) return;
    setPublishModalVisible(true);
  };

  /** 确认发布 */
  const handleConfirmPublish = async () => {
    if (!generatedArticle || !publishAccountId) {
      message.warning('请选择发布账号');
      return;
    }
    setPublishLoading(true);
    try {
      // 先保存文章
      const articleData = {
        title: generatedArticle.title,
        content: generatedArticle.content,
        tags: generatedArticle.tags,
        summary: generatedArticle.summary,
      };
      const res = await articleAPI.create(articleData);
      const savedArticle = res.data;

      // 创建发布任务
      await publishAPI.now({
        article_id: savedArticle.id,
        account_id: publishAccountId,
      });

      message.success('发布任务已创建！');
      setPublishModalVisible(false);
      setPublishAccountId(undefined);
      clearGenerated();
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      message.error(detail || '发布失败');
    } finally {
      setPublishLoading(false);
    }
  };

  /** 复制内容到剪贴板 */
  const handleCopy = () => {
    if (!generatedArticle) return;
    const text = `# ${generatedArticle.title}\n\n${generatedArticle.content}`;
    navigator.clipboard.writeText(text).then(
      () => { message.success('已复制到剪贴板'); },
      () => { message.error('复制失败，请手动复制'); }
    );
  };

  // ==================== 系列文章处理函数 ====================

  /** 生成系列大纲 */
  const handleGenerateOutline = async () => {
    try {
      const values = await seriesForm.validateFields(['seriesTopic', 'seriesCount', 'seriesProvider']);
      setSeriesOutlineLoading(true);
      setSeriesOutline(null);
      setSeriesArticles([]);

      const res = await articleAPI.seriesOutline({
        topic: values.seriesTopic,
        count: values.seriesCount,
        ai_provider: values.seriesProvider,
      });
      setSeriesOutline(res.data);
      message.success('系列大纲生成成功！');
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('系列大纲生成失败，请重试');
    } finally {
      setSeriesOutlineLoading(false);
    }
  };

  /** 更新大纲中某篇文章的标题 */
  const handleOutlineTitleChange = (index: number, newTitle: string) => {
    if (!seriesOutline) return;
    const updated = { ...seriesOutline };
    updated.articles = [...updated.articles];
    updated.articles[index] = { ...updated.articles[index], title: newTitle };
    setSeriesOutline(updated);
  };

  /** 批量生成系列文章 */
  const handleSeriesGenerate = async () => {
    if (!seriesOutline) return;
    try {
      const values = await seriesForm.validateFields(['seriesStyle', 'seriesWordCount', 'seriesProvider']);
      setSeriesGenerating(true);
      setSeriesProgress({ current: 0, total: seriesOutline.articles.length });
      setSeriesArticles([]);

      const res = await articleAPI.seriesGenerate({
        series_title: seriesOutline.series_title,
        articles: seriesOutline.articles.map((a) => ({
          title: a.title,
          description: a.description,
          key_points: a.key_points,
        })),
        style: values.seriesStyle,
        word_count: values.seriesWordCount,
        ai_provider: values.seriesProvider,
      });

      const articles = res.data ?? [];
      setSeriesArticles(articles);
      setSeriesProgress({ current: articles.length, total: seriesOutline.articles.length });
      message.success(`成功生成 ${articles.length} 篇系列文章！`);
    } catch (error: any) {
      if (error?.errorFields) return;
      const detail = error?.response?.data?.detail;
      message.error(detail || '系列文章生成失败，请重试');
    } finally {
      setSeriesGenerating(false);
    }
  };

  /** 判断是否正在加载中（流式生成或传统生成） */
  const isLoading = isStreaming;

  return (
    <div>
    <Tabs
      activeKey={activeTab}
      onChange={setActiveTab}
      style={{ marginBottom: 16 }}
      items={[
        {
          key: 'single',
          label: (
            <span>
              <FileTextOutlined style={{ marginRight: 4 }} />
              单篇生成
            </span>
          ),
        },
        {
          key: 'series',
          label: (
            <span>
              <OrderedListOutlined style={{ marginRight: 4 }} />
              系列生成
            </span>
          ),
        },
        {
          key: 'agent',
          label: (
            <span>
              <ThunderboltOutlined style={{ marginRight: 4 }} />
              智能体生成
            </span>
          ),
        },
        {
          key: 'story',
          label: (
            <span>
              <EditOutlined style={{ marginRight: 4 }} />
              故事生成
            </span>
          ),
        },
      ]}
    />

    {activeTab === 'single' ? (
    <Row gutter={[16, 16]}>
      {/* 左侧：生成表单 */}
      <Col xs={24} lg={10}>
        <Card
          title={
            <span style={{ color: colors.textPrimary }}>
              <RobotOutlined style={{ marginRight: 8, color: colors.primary }} />
              AI 文章生成
            </span>
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
          }}
          headStyle={{ borderBottom: `1px solid ${colors.border}` }}
        >
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              style: 'professional',
              wordCount: 1000,
              provider: 'gemini',
              enableImages: false,
            }}
          >
            {/* 主题输入 */}
            <Form.Item
              label="文章主题"
              name="topic"
              rules={[{ required: true, message: '请输入文章主题' }]}
            >
              <TextArea
                rows={3}
                placeholder="请输入文章主题或关键词，如：深度学习在自然语言处理中的应用"
                maxLength={500}
                showCount
                style={{ background: colors.bgInput, borderColor: colors.border }}
              />
            </Form.Item>

            {/* 文章风格 */}
            <Form.Item
              label="写作风格"
              name="style"
              rules={[{ required: true, message: '请选择写作风格' }]}
            >
              <Select
                options={styleOptions}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* 目标字数 */}
            <Form.Item
              label="目标字数"
              name="wordCount"
              rules={[{ required: true, message: '请选择目标字数' }]}
            >
              <Select
                options={wordCountOptions}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* AI提供商 */}
            <Form.Item
              label="AI 提供商"
              name="provider"
              rules={[{ required: true, message: '请选择AI提供商' }]}
            >
              <Select
                options={providerOptions}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* 内容模板选择 */}
            <Form.Item label="模板">
              <Select
                placeholder="选择内容模板（可选）"
                value={selectedTemplateId}
                onChange={handleTemplateChange}
                allowClear
                style={{ width: '100%' }}
                options={templates.map((t) => ({
                  label: t.name + (t.description ? ` - ${t.description}` : ''),
                  value: t.id,
                }))}
              />
            </Form.Item>

            {/* AI 配图开关 */}
            <Form.Item
              label={
                <span>
                  <PictureOutlined style={{ marginRight: 4 }} />
                  AI 智能配图
                </span>
              }
              name="enableImages"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
              />
            </Form.Item>

            {/* 生成按钮 */}
            <Form.Item>
              <Button
                type="primary"
                icon={<RobotOutlined />}
                size="large"
                block
                loading={isLoading}
                onClick={handleGenerate}
                style={{
                  height: 48,
                  fontSize: 16,
                  fontWeight: 600,
                  borderRadius: 8,
                  background: 'linear-gradient(135deg, #1677ff 0%, #4096ff 100%)',
                }}
              >
                {isLoading ? 'AI 正在生成中...' : '一键生成文章'}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Col>

      {/* 右侧：生成结果预览 */}
      <Col xs={24} lg={14}>
        <Card
          title={
            <span style={{ color: colors.textPrimary }}>
              <FilePreviewIcon />
              生成结果预览
            </span>
          }
          extra={
            generatedArticle ? (
              <Space>
                <Button
                  icon={<CopyOutlined />}
                  size="small"
                  onClick={handleCopy}
                >
                  复制
                </Button>
              </Space>
            ) : null
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
            minHeight: 500,
          }}
          headStyle={{ borderBottom: `1px solid ${colors.border}` }}
        >
          {isStreaming ? (
            /* ---- 流式生成中：实时显示内容 + 脉冲光标 ---- */
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 16,
                  color: colors.primary,
                  fontSize: 14,
                }}
              >
                <Spin size="small" />
                <Text style={{ color: colors.primary }}>AI 正在实时生成中...</Text>
              </div>
              <div
                style={{
                  color: colors.textPrimary,
                  lineHeight: 1.8,
                  maxHeight: 500,
                  overflowY: 'auto',
                  paddingRight: 8,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace',
                  fontSize: 14,
                }}
              >
                {streamingContent}
                {/* 脉冲光标指示器 */}
                <span
                  style={{
                    display: 'inline-block',
                    width: 2,
                    height: 18,
                    background: '#1677ff',
                    marginLeft: 2,
                    verticalAlign: 'text-bottom',
                    animation: 'streamingCursorBlink 1s ease-in-out infinite',
                  }}
                />
              </div>
            </div>
          ) : generatedArticle ? (
            <div>
              {/* 文章标题 */}
              <Title
                level={3}
                style={{ color: colors.textPrimary, marginBottom: 12 }}
              >
                {generatedArticle.title}
              </Title>

              {/* 文章元信息 */}
              <div
                style={{
                  display: 'flex',
                  gap: 16,
                  marginBottom: 16,
                  color: colors.textSecondary,
                  fontSize: 13,
                }}
              >
                <span>字数：{generatedArticle.word_count}</span>
              </div>

              {/* 标签 */}
              {generatedArticle.tags && generatedArticle.tags.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <TagsOutlined style={{ marginRight: 8, color: colors.primary }} />
                  {generatedArticle.tags.map((tag, i) => (
                    <Tag key={i} color="blue" style={{ marginBottom: 4 }}>
                      {tag}
                    </Tag>
                  ))}
                </div>
              )}

              <Divider style={{ borderColor: colors.border }} />

              {/* 文章正文（Markdown渲染） */}
              <div
                style={{
                  color: colors.textPrimary,
                  lineHeight: 1.8,
                  maxHeight: 500,
                  overflowY: 'auto',
                  paddingRight: 8,
                }}
                dangerouslySetInnerHTML={{
                  __html: renderMarkdown(generatedArticle.content),
                }}
              />

              <Divider style={{ borderColor: colors.border }} />

              {/* 操作按钮 */}
              <Space size="middle" wrap>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSaveDraft}
                  loading={saving}
                  style={{ borderRadius: 6 }}
                >
                  保存草稿
                </Button>
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handlePublish}
                  loading={saving}
                  style={{
                    borderRadius: 6,
                    background: '#52c41a',
                    borderColor: '#52c41a',
                  }}
                >
                  直接发布
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleGenerate}
                  loading={isLoading}
                  style={{ borderRadius: 6 }}
                >
                  重新生成
                </Button>
              </Space>
            </div>
          ) : (
            <Empty
              description={
                <Text style={{ color: colors.textTertiary }}>
                  在左侧填写主题和参数后，点击"一键生成文章"
                </Text>
              }
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 400,
              }}
            />
          )}
        </Card>
      </Col>
      {/* 发布账号选择弹窗 */}
      <Modal
        title="选择发布账号"
        open={publishModalVisible}
        onOk={handleConfirmPublish}
        onCancel={() => setPublishModalVisible(false)}
        confirmLoading={publishLoading}
        okText="确认发布"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <Text style={{ color: colors.textSecondary }}>
            文章将保存并立即创建发布任务
          </Text>
        </div>
        <Select
          placeholder="选择发布账号"
          value={publishAccountId}
          onChange={setPublishAccountId}
          style={{ width: '100%' }}
          options={accounts.filter(a => a.login_status === 'logged_in').map(a => ({
            label: a.nickname || '未命名',
            value: a.id,
          }))}
        />
      </Modal>
    </Row>
    ) : activeTab === 'series' ? (
    /* ==================== 系列文章生成 Tab ==================== */
    <Row gutter={[16, 16]}>
      {/* 左侧：系列参数表单 */}
      <Col xs={24} lg={10}>
        <Card
          title={
            <span style={{ color: colors.textPrimary }}>
              <OrderedListOutlined style={{ marginRight: 8, color: colors.primary }} />
              系列文章生成
            </span>
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
          }}
          headStyle={{ borderBottom: `1px solid ${colors.border}` }}
        >
          <Form
            form={seriesForm}
            layout="vertical"
            initialValues={{
              seriesCount: 5,
              seriesProvider: 'gemini',
              seriesStyle: 'professional',
              seriesWordCount: 1500,
            }}
          >
            {/* 系列主题 */}
            <Form.Item
              label="系列主题"
              name="seriesTopic"
              rules={[{ required: true, message: '请输入系列主题' }]}
            >
              <Input.TextArea
                rows={3}
                placeholder="请输入系列文章的总主题，如：Python 从入门到精通"
                maxLength={200}
                showCount
                style={{ background: colors.bgInput, borderColor: colors.border }}
              />
            </Form.Item>

            {/* 文章数量 */}
            <Form.Item
              label="文章数量"
              name="seriesCount"
              rules={[{ required: true, message: '请选择文章数量' }]}
            >
              <InputNumber
                min={2}
                max={20}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* AI提供商 */}
            <Form.Item
              label="AI 提供商"
              name="seriesProvider"
              rules={[{ required: true, message: '请选择AI提供商' }]}
            >
              <Select
                options={providerOptions}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* 写作风格 */}
            <Form.Item
              label="写作风格"
              name="seriesStyle"
              rules={[{ required: true, message: '请选择写作风格' }]}
            >
              <Select
                options={styleOptions}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* 每篇字数 */}
            <Form.Item
              label="每篇目标字数"
              name="seriesWordCount"
              rules={[{ required: true, message: '请选择目标字数' }]}
            >
              <Select
                options={wordCountOptions}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* 生成大纲按钮 */}
            <Form.Item>
              <Button
                type="primary"
                icon={<OrderedListOutlined />}
                size="large"
                block
                loading={seriesOutlineLoading}
                onClick={handleGenerateOutline}
                style={{
                  height: 48,
                  fontSize: 16,
                  fontWeight: 600,
                  borderRadius: 8,
                  background: 'linear-gradient(135deg, #1677ff 0%, #4096ff 100%)',
                }}
              >
                {seriesOutlineLoading ? '正在生成大纲...' : '生成系列大纲'}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Col>

      {/* 右侧：大纲预览与文章生成 */}
      <Col xs={24} lg={14}>
        <Card
          title={
            <span style={{ color: colors.textPrimary }}>
              <FilePreviewIcon />
              系列大纲 & 进度
            </span>
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
            minHeight: 500,
          }}
          headStyle={{ borderBottom: `1px solid ${colors.border}` }}
        >
          {seriesOutlineLoading ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 400,
                gap: 16,
              }}
            >
              <Spin size="large" />
              <Text style={{ color: colors.textSecondary }}>
                AI 正在规划系列文章大纲，请稍候...
              </Text>
            </div>
          ) : seriesOutline ? (
            <div>
              {/* 系列标题和描述 */}
              <Title level={4} style={{ color: colors.textPrimary, marginBottom: 8 }}>
                {seriesOutline.series_title}
              </Title>
              <Text style={{ color: colors.textSecondary, display: 'block', marginBottom: 16 }}>
                {seriesOutline.description}
              </Text>

              <Divider style={{ borderColor: colors.border }} />

              {/* 大纲文章列表（可编辑标题） */}
              <List
                dataSource={seriesOutline.articles}
                renderItem={(item: SeriesOutlineArticle, index: number) => (
                  <List.Item
                    style={{
                      borderBottom: `1px solid ${colors.border}`,
                      padding: '12px 0',
                    }}
                  >
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                        <Tag color="blue" style={{ marginRight: 0 }}>
                          第 {item.order} 篇
                        </Tag>
                        <Input
                          value={item.title}
                          onChange={(e) => handleOutlineTitleChange(index, e.target.value)}
                          style={{
                            flex: 1,
                            background: colors.bgInput,
                            borderColor: colors.border,
                            color: colors.textPrimary,
                          }}
                          disabled={seriesGenerating}
                        />
                      </div>
                      <Text style={{ color: colors.textSecondary, fontSize: 13, display: 'block', marginBottom: 4 }}>
                        {item.description}
                      </Text>
                      <div>
                        {item.key_points.map((point, pi) => (
                          <Tag key={pi} style={{ marginBottom: 4 }}>
                            {point}
                          </Tag>
                        ))}
                      </div>
                      {/* 已生成标记 */}
                      {seriesArticles[index] && (
                        <div style={{ marginTop: 8 }}>
                          <Tag color="green" icon={<CheckCircleOutlined />}>
                            已生成 - {seriesArticles[index].word_count} 字
                          </Tag>
                        </div>
                      )}
                    </div>
                  </List.Item>
                )}
              />

              <Divider style={{ borderColor: colors.border }} />

              {/* 生成进度 */}
              {seriesGenerating && (
                <div style={{ marginBottom: 16 }}>
                  <Text style={{ color: colors.textSecondary, display: 'block', marginBottom: 8 }}>
                    正在生成第 {seriesProgress.current + 1} / {seriesProgress.total} 篇...
                  </Text>
                  <Progress
                    percent={seriesProgress.total > 0 ? Math.round((seriesProgress.current / seriesProgress.total) * 100) : 0}
                    status="active"
                    strokeColor="#1677ff"
                  />
                </div>
              )}

              {/* 生成完成 */}
              {seriesArticles.length > 0 && !seriesGenerating && (
                <div style={{ marginBottom: 16 }}>
                  <Tag color="green" icon={<CheckCircleOutlined />} style={{ fontSize: 14, padding: '4px 12px' }}>
                    全部 {seriesArticles.length} 篇文章已生成并保存为草稿
                  </Tag>
                </div>
              )}

              {/* 批量生成按钮 */}
              <Button
                type="primary"
                icon={<RobotOutlined />}
                size="large"
                block
                loading={seriesGenerating}
                onClick={handleSeriesGenerate}
                disabled={seriesArticles.length === seriesOutline.articles.length}
                style={{
                  height: 48,
                  fontSize: 16,
                  fontWeight: 600,
                  borderRadius: 8,
                  background: seriesArticles.length === seriesOutline.articles.length
                    ? undefined
                    : 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)',
                }}
              >
                {seriesGenerating
                  ? `正在生成中 (${seriesProgress.current}/${seriesProgress.total})...`
                  : seriesArticles.length === seriesOutline.articles.length
                  ? '全部文章已生成'
                  : '批量生成文章'}
              </Button>
            </div>
          ) : (
            <Empty
              description={
                <Text style={{ color: colors.textTertiary }}>
                  在左侧填写系列主题和参数后，点击"生成系列大纲"
                </Text>
              }
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 400,
              }}
            />
          )}
        </Card>
      </Col>
    </Row>
    ) : activeTab === 'agent' ? (
    /* ==================== 智能体生成 Tab ==================== */
    <Row gutter={[16, 16]}>
      {/* 左侧：智能体参数 */}
      <Col xs={24} lg={10}>
        <Card
          title={
            <span style={{ color: colors.textPrimary }}>
              <ThunderboltOutlined style={{ marginRight: 8, color: colors.warning }} />
              智能体生成
            </span>
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
          }}
          headStyle={{ borderBottom: `1px solid ${colors.border}` }}
        >
          <Alert
            message="选择已有文章作为参考，智能体将自动分析主题和风格，规划并生成全新的相关文章"
            type="info"
            showIcon
            style={{ marginBottom: 20, background: '#111a2c', borderColor: '#15325b' }}
          />
          <Form
            form={agentForm}
            layout="vertical"
            initialValues={{
              agentCount: 5,
              agentProvider: 'gemini',
              agentWordCount: 1500,
            }}
          >
            {/* 选择参考文章 */}
            <Form.Item
              label="选择参考文章"
              name="articleIds"
              rules={[{ required: true, message: '请选择至少一篇参考文章' }]}
            >
              <Select
                mode="multiple"
                placeholder="选择 1-10 篇已有文章作为参考"
                loading={agentSourceLoading}
                maxCount={10}
                style={{ width: '100%' }}
                optionFilterProp="label"
                options={agentSourceArticles.map((a) => ({
                  label: `[${a.id}] ${a.title}`,
                  value: a.id,
                }))}
              />
            </Form.Item>

            {/* 生成数量 */}
            <Form.Item
              label="生成文章数量"
              name="agentCount"
              rules={[{ required: true, message: '请输入数量' }]}
            >
              <InputNumber min={1} max={20} style={{ width: '100%' }} />
            </Form.Item>

            {/* AI提供商 */}
            <Form.Item
              label="AI 提供商"
              name="agentProvider"
              rules={[{ required: true, message: '请选择AI提供商' }]}
            >
              <Select options={providerOptions} style={{ width: '100%' }} />
            </Form.Item>

            {/* 写作风格 */}
            <Form.Item
              label="写作风格（留空则 AI 自动推荐）"
              name="agentStyle"
            >
              <Select
                allowClear
                placeholder="留空 = AI 自动推荐风格"
                options={styleOptions}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* 每篇字数 */}
            <Form.Item
              label="每篇目标字数"
              name="agentWordCount"
              rules={[{ required: true, message: '请选择字数' }]}
            >
              <Select options={wordCountOptions} style={{ width: '100%' }} />
            </Form.Item>

            {/* 生成按钮 */}
            <Form.Item>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                size="large"
                block
                loading={agentLoading}
                onClick={handleAgentGenerate}
                style={{
                  height: 48,
                  fontSize: 16,
                  fontWeight: 600,
                  borderRadius: 8,
                  background: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)',
                  borderColor: '#faad14',
                  color: '#000',
                }}
              >
                {agentLoading ? '智能体正在工作中...' : '一键智能生成'}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Col>

      {/* 右侧：生成结果 */}
      <Col xs={24} lg={14}>
        <Card
          title={
            <span style={{ color: colors.textPrimary }}>
              <FilePreviewIcon />
              智能体生成结果
            </span>
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
            minHeight: 500,
          }}
          headStyle={{ borderBottom: `1px solid ${colors.border}` }}
        >
          {agentLoading ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 400,
                gap: 16,
              }}
            >
              <Spin size="large" />
              <Text style={{ color: colors.textSecondary }}>
                智能体正在分析参考文章、规划大纲并逐篇生成中...
              </Text>
              <Steps
                direction="vertical"
                size="small"
                current={-1}
                status="process"
                items={[
                  { title: '分析参考文章', description: '提取主题、风格、关键词' },
                  { title: '规划文章大纲', description: '设计差异化角度和结构' },
                  { title: '逐篇生成文章', description: '批量生成完整文章' },
                ]}
                style={{ marginTop: 16 }}
              />
            </div>
          ) : agentArticles.length > 0 ? (
            <div>
              <div style={{ marginBottom: 16 }}>
                <Tag color="green" icon={<CheckCircleOutlined />} style={{ fontSize: 14, padding: '4px 12px' }}>
                  智能体成功生成 {agentArticles.length} 篇文章，已保存为草稿
                </Tag>
              </div>
              <List
                dataSource={agentArticles}
                renderItem={(item: Article, index: number) => (
                  <List.Item
                    style={{
                      borderBottom: `1px solid ${colors.border}`,
                      padding: '12px 0',
                    }}
                  >
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                        <Tag color="blue">第 {index + 1} 篇</Tag>
                        <Text strong style={{ color: colors.textPrimary, flex: 1 }}>
                          {item.title}
                        </Text>
                        <Tag>{item.word_count} 字</Tag>
                      </div>
                      <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
                        {item.summary}
                      </Text>
                      {item.tags && item.tags.length > 0 && (
                        <div style={{ marginTop: 8 }}>
                          {item.tags.map((tag, ti) => (
                            <Tag key={ti} style={{ marginBottom: 4 }}>{tag}</Tag>
                          ))}
                        </div>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </div>
          ) : (
            <Empty
              description={
                <Text style={{ color: colors.textTertiary }}>
                  选择参考文章后，点击"一键智能生成"，智能体将自动分析并批量生成相关文章
                </Text>
              }
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 400,
              }}
            />
          )}
        </Card>
      </Col>
    </Row>
    ) : activeTab === 'story' ? (
    <Row gutter={[16, 16]}>
      {/* 左侧：故事生成表单 */}
      <Col xs={24} lg={10}>
        <Card
          title={
            <span style={{ color: colors.textPrimary }}>
              <EditOutlined style={{ marginRight: 8, color: colors.accent }} />
              故事生成
            </span>
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
          }}
          headStyle={{ borderBottom: `1px solid ${colors.border}` }}
        >
          <Alert
            message="基于参考素材生成知乎盐选风格故事"
            description="粘贴新闻报道、背景资料或故事种子，AI 将自动提取人物和冲突，规划章节大纲，逐章生成完整故事，并进行去 AI 味润色。"
            type="info"
            showIcon
            style={{ marginBottom: 16, background: '#1a1a2e', borderColor: colors.border }}
          />

          <Form
            form={storyForm}
            layout="vertical"
            initialValues={{
              chapterCount: 5,
              totalWordCount: 15000,
              storyType: 'corruption',
              storyProvider: 'gemini',
            }}
          >
            {/* 参考素材 */}
            <Form.Item
              label={<span style={{ color: colors.textPrimary }}>参考素材（必填）</span>}
              name="referenceText"
              rules={[
                { required: true, message: '请输入参考素材' },
                { min: 50, message: '素材至少 50 字' },
              ]}
            >
              <TextArea
                rows={8}
                placeholder="粘贴新闻报道、背景资料、案件描述或故事种子……&#10;&#10;例如：2003年某县副县长张某因受贿800万被双规，其妻在得知消息后……"
                maxLength={50000}
                showCount
                style={{
                  background: colors.bgInput,
                  borderColor: '#303050',
                  color: colors.textPrimary,
                }}
              />
            </Form.Item>

            {/* 可选：参考文章 */}
            <Form.Item
              label={<span style={{ color: colors.textPrimary }}>参考已有文章（可选）</span>}
              name="storyArticleIds"
            >
              <Select
                mode="multiple"
                allowClear
                placeholder="可选择已有文章作为额外参考"
                maxCount={5}
                loading={agentSourceLoading}
                options={agentSourceArticles.map((a) => ({
                  label: `[${a.id}] ${a.title}`,
                  value: a.id,
                }))}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* 故事类型 */}
            <Form.Item
              label={<span style={{ color: colors.textPrimary }}>故事类型</span>}
              name="storyType"
            >
              <Select
                options={[
                  { label: '反腐纪实', value: 'corruption' },
                  { label: '历史纪事', value: 'historical' },
                  { label: '悬疑推理', value: 'suspense' },
                  { label: '情感纪实', value: 'romance' },
                  { label: '职场风云', value: 'workplace' },
                ]}
              />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                {/* 章节数 */}
                <Form.Item
                  label={<span style={{ color: colors.textPrimary }}>章节数</span>}
                  name="chapterCount"
                >
                  <Select
                    options={[
                      { label: '3 章（短篇）', value: 3 },
                      { label: '5 章（中篇）', value: 5 },
                      { label: '7 章（长篇）', value: 7 },
                      { label: '8 章（长篇）', value: 8 },
                    ]}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                {/* 总字数 */}
                <Form.Item
                  label={<span style={{ color: colors.textPrimary }}>总字数</span>}
                  name="totalWordCount"
                >
                  <Select
                    options={[
                      { label: '8000 字', value: 8000 },
                      { label: '12000 字', value: 12000 },
                      { label: '15000 字', value: 15000 },
                      { label: '20000 字', value: 20000 },
                      { label: '25000 字', value: 25000 },
                    ]}
                  />
                </Form.Item>
              </Col>
            </Row>

            {/* AI 提供商 */}
            <Form.Item
              label={<span style={{ color: colors.textPrimary }}>AI 提供商</span>}
              name="storyProvider"
            >
              <Select options={providerOptions} />
            </Form.Item>

            {/* 生成按钮 */}
            <Form.Item>
              <Button
                type="primary"
                size="large"
                block
                loading={storyLoading}
                onClick={handleStoryGenerate}
                icon={<EditOutlined />}
                style={{
                  height: 48,
                  fontSize: 16,
                  background: storyLoading ? undefined : 'linear-gradient(135deg, #722ed1 0%, #9254de 100%)',
                  border: 'none',
                  borderRadius: 8,
                }}
              >
                {storyLoading ? '故事生成中（约5-10分钟）...' : '开始生成故事'}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Col>

      {/* 右侧：结果展示 */}
      <Col xs={24} lg={14}>
        <Card
          title={
            <span style={{ color: colors.textPrimary }}>
              <FileTextOutlined style={{ marginRight: 8, color: colors.accent }} />
              生成结果
            </span>
          }
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
            minHeight: 500,
          }}
          headStyle={{ borderBottom: `1px solid ${colors.border}` }}
        >
          {storyLoading ? (
            <div style={{ textAlign: 'center', padding: '40px 20px' }}>
              <Spin size="large" />
              <div style={{ marginTop: 24 }}>
                <Steps
                  direction="vertical"
                  current={storyPhase}
                  size="small"
                  items={[
                    {
                      title: '素材提取',
                      description: '分析参考素材的人物、时代、冲突',
                    },
                    {
                      title: '故事规划',
                      description: '设计故事弧线、人物卡片、章节大纲',
                    },
                    {
                      title: '分章生成',
                      description: '逐章生成 2000-3000 字内容',
                    },
                    {
                      title: '组装润色',
                      description: '合并章节、添加过渡和伏笔回收',
                    },
                    {
                      title: '去AI味',
                      description: '替换模板表达、添加自然语感',
                    },
                  ]}
                />
              </div>
            </div>
          ) : storyArticles.length > 0 ? (
            <div>
              <Alert
                message={`故事生成完成：共 ${storyArticles.length} 篇（1篇完整故事 + ${storyArticles.length - 1}篇分章）`}
                type="success"
                showIcon
                style={{ marginBottom: 16, background: '#1a2e1a', borderColor: '#2a3e2a' }}
              />
              <List
                dataSource={storyArticles}
                renderItem={(item, index) => (
                  <List.Item
                    style={{
                      borderBottom: `1px solid ${colors.border}`,
                      padding: '12px 0',
                    }}
                  >
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <Tag color={index === 0 ? 'green' : 'purple'}>
                          {index === 0 ? '完整故事' : `第${item.series_order || index}章`}
                        </Tag>
                        <Text strong style={{ color: colors.textPrimary, flex: 1 }}>
                          {item.title}
                        </Text>
                        <Tag>{item.word_count} 字</Tag>
                      </div>
                      <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
                        {item.summary?.substring(0, 100)}
                        {(item.summary?.length || 0) > 100 ? '...' : ''}
                      </Text>
                      {index === 0 && item.tags && item.tags.length > 0 && (
                        <div style={{ marginTop: 8 }}>
                          {item.tags.map((tag, ti) => (
                            <Tag key={ti} style={{ marginBottom: 4 }}>{tag}</Tag>
                          ))}
                        </div>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </div>
          ) : (
            <Empty
              description={
                <Text style={{ color: colors.textTertiary }}>
                  粘贴参考素材后，点击"开始生成故事"，AI 将自动生成多章节知乎盐选故事
                </Text>
              }
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 400,
              }}
            />
          )}
        </Card>
      </Col>
    </Row>
    ) : null}
    </div>
  );
};

/** 文件预览图标组件 */
const FilePreviewIcon: React.FC = () => (
  <FileTextOutlined style={{ marginRight: 8, color: colors.primary }} />
);

export default ArticleGenerate;
