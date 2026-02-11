import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  Popconfirm,
  message,
  Row,
  Col,
  Modal,
  InputNumber,
  Skeleton,
  Upload,
} from 'antd';
import {
  SearchOutlined,
  DeleteOutlined,
  SendOutlined,
  ReloadOutlined,
  FileTextOutlined,
  EyeOutlined,
  EditOutlined,
  ImportOutlined,
  ExportOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useArticleStore } from '../../stores/articleStore';
import { useAccountStore } from '../../stores/accountStore';
import { publishAPI, articleAPI } from '../../services/api';
import MarkdownEditor from '../../components/MarkdownEditor';
import type { Article, ArticleStatus } from '../../utils/types';
import type { ColumnsType } from 'antd/es/table';
import type { RcFile } from 'antd/es/upload/interface';

const { Text, Paragraph } = Typography;

/** 状态颜色映射 */
const statusConfig: Record<
  ArticleStatus,
  { color: string; text: string }
> = {
  draft: { color: 'default', text: '草稿' },
  pending: { color: 'blue', text: '待发布' },
  published: { color: 'green', text: '已发布' },
  failed: { color: 'red', text: '发布失败' },
};

/** AI提供商文字映射 */
const providerTextMap: Record<string, string> = {
  openai: 'OpenAI',
  deepseek: 'DeepSeek',
  claude: 'Claude',
  manual: '手动创建',
  rewrite: '改写',
  import: '导入',
};

/** 改写风格选项 */
const rewriteStyleOptions = [
  { label: '专业严谨', value: 'professional' },
  { label: '轻松活泼', value: 'casual' },
  { label: '幽默风趣', value: 'humorous' },
  { label: '精简浓缩', value: 'simplified' },
  { label: '扩展丰富', value: 'expanded' },
];

/** 文章分类选项 */
const categoryOptions = [
  { label: '科技', value: '科技' },
  { label: '财经', value: '财经' },
  { label: '教育', value: '教育' },
  { label: '健康', value: '健康' },
  { label: '生活', value: '生活' },
  { label: '职场', value: '职场' },
  { label: '编程', value: '编程' },
  { label: 'AI', value: 'AI' },
  { label: '其他', value: '其他' },
];

/** 分类颜色映射 */
const categoryColorMap: Record<string, string> = {
  '科技': 'blue',
  '财经': 'gold',
  '教育': 'cyan',
  '健康': 'green',
  '生活': 'orange',
  '职场': 'purple',
  '编程': 'geekblue',
  'AI': 'magenta',
  '其他': 'default',
};

const ArticleList: React.FC = () => {
  const {
    articles,
    total,
    loading,
    currentPage,
    pageSize,
    fetchArticles,
    deleteArticle,
    batchDeleteArticles,
  } = useArticleStore();

  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [previewArticle, setPreviewArticle] = useState<Article | null>(null);
  const [previewEditMode, setPreviewEditMode] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const { accounts, fetchAccounts: fetchAccountList } = useAccountStore();
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [batchAccountId, setBatchAccountId] = useState<number | undefined>(undefined);
  const [batchInterval, setBatchInterval] = useState(10);
  const [batchPublishing, setBatchPublishing] = useState(false);

  const [initialLoading, setInitialLoading] = useState(true);

  // ---- 改写相关状态 ----
  const [rewriteModalVisible, setRewriteModalVisible] = useState(false);
  const [rewriteArticle, setRewriteArticle] = useState<Article | null>(null);
  const [rewriteStyle, setRewriteStyle] = useState('professional');
  const [rewriteInstruction, setRewriteInstruction] = useState('');
  const [rewriteLoading, setRewriteLoading] = useState(false);

  // ---- 导入相关状态 ----
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [importLoading, setImportLoading] = useState(false);

  useEffect(() => {
    fetchArticles({ page: 1, page_size: 10 }).finally(() => {
      setInitialLoading(false);
    });
  }, []);

  useEffect(() => {
    fetchAccountList();
  }, []);

  /** 搜索 */
  const handleSearch = () => {
    fetchArticles({
      page: 1,
      page_size: pageSize,
      keyword: keyword || undefined,
      status: statusFilter as ArticleStatus | undefined,
      category: categoryFilter || undefined,
    });
  };

  /** 翻页 */
  const handlePageChange = (page: number, size: number) => {
    fetchArticles({
      page,
      page_size: size,
      keyword: keyword || undefined,
      status: statusFilter as ArticleStatus | undefined,
      category: categoryFilter || undefined,
    });
  };

  /** 删除单篇文章 */
  const handleDelete = async (id: number) => {
    try {
      await deleteArticle(id);
      message.success('删除成功');
    } catch {
      message.error('删除失败');
    }
  };

  /** 批量删除 */
  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择文章');
      return;
    }
    try {
      await batchDeleteArticles(selectedRowKeys as number[]);
      setSelectedRowKeys([]);
      message.success(`成功删除 ${selectedRowKeys.length} 篇文章`);
    } catch {
      message.error('批量删除失败');
    }
  };

  /** 批量发布 */
  const handleBatchPublish = async () => {
    if (!batchAccountId) {
      message.warning('请选择发布账号');
      return;
    }
    setBatchPublishing(true);
    try {
      await publishAPI.batch({
        article_ids: selectedRowKeys as number[],
        account_id: batchAccountId,
        interval_minutes: batchInterval,
      });
      message.success(`已创建 ${selectedRowKeys.length} 个发布任务`);
      setBatchModalVisible(false);
      setSelectedRowKeys([]);
      setBatchAccountId(undefined);
      setBatchInterval(10);
    } catch {
      message.error('创建批量发布任务失败');
    } finally {
      setBatchPublishing(false);
    }
  };

  /** 打开改写弹窗 */
  const handleOpenRewrite = (record: Article) => {
    setRewriteArticle(record);
    setRewriteStyle('professional');
    setRewriteInstruction('');
    setRewriteModalVisible(true);
  };

  /** 执行改写 */
  const handleRewrite = async () => {
    if (!rewriteArticle) return;
    setRewriteLoading(true);
    try {
      await articleAPI.rewrite({
        article_id: rewriteArticle.id,
        style: rewriteStyle,
        instruction: rewriteInstruction || undefined,
      });
      message.success('文章改写成功，已保存为新草稿');
      setRewriteModalVisible(false);
      setRewriteArticle(null);
      // 刷新文章列表
      fetchArticles({ page: currentPage, page_size: pageSize });
    } catch {
      message.error('文章改写失败，请重试');
    } finally {
      setRewriteLoading(false);
    }
  };

  /** 打开预览（重置编辑模式） */
  const handleOpenPreview = (record: Article) => {
    setPreviewArticle(record);
    setPreviewEditMode(false);
    setEditContent(record.content);
  };

  /** 切换编辑模式 */
  const handleToggleEditMode = () => {
    if (!previewEditMode && previewArticle) {
      setEditContent(previewArticle.content);
    }
    setPreviewEditMode(!previewEditMode);
  };

  /** 保存编辑内容 */
  const handleSaveEdit = async () => {
    if (!previewArticle) return;
    setEditSaving(true);
    try {
      await articleAPI.update(previewArticle.id, { content: editContent });
      message.success('文章内容已保存');
      setPreviewEditMode(false);
      fetchArticles({ page: currentPage, page_size: pageSize });
      setPreviewArticle({ ...previewArticle, content: editContent });
    } catch {
      message.error('保存失败，请重试');
    } finally {
      setEditSaving(false);
    }
  };

  /** 导入文件 */
  const handleImportFile = async (file: RcFile) => {
    setImportLoading(true);
    try {
      await articleAPI.import(file as File);
      message.success(`文件 "${file.name}" 导入成功`);
      setImportModalVisible(false);
      fetchArticles({ page: 1, page_size: pageSize });
    } catch {
      message.error('文件导入失败，请检查文件格式');
    } finally {
      setImportLoading(false);
    }
    return false;
  };

  /** 导出文章 */
  const handleExport = () => {
    const link = document.createElement('a');
    link.href = '/api/articles/export?format=csv';
    link.download = 'articles_export.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    message.success('文章导出中...');
  };

  /** 表格列定义 */
  const columns: ColumnsType<Article> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text: string, record: Article) => (
        <a
          onClick={() => handleOpenPreview(record)}
          style={{ color: '#1677ff' }}
        >
          {text}
        </a>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 90,
      render: (category: string | null | undefined) =>
        category ? (
          <Tag color={categoryColorMap[category] || 'default'}>{category}</Tag>
        ) : (
          <Text style={{ color: '#555' }}>-</Text>
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ArticleStatus) => (
        <Tag color={statusConfig[status]?.color}>
          {statusConfig[status]?.text || status}
        </Tag>
      ),
    },
    {
      title: '字数',
      dataIndex: 'word_count',
      key: 'word_count',
      width: 80,
      render: (count: number) => (
        <Text style={{ color: '#a0a0a0' }}>{count}</Text>
      ),
    },
    {
      title: '来源',
      dataIndex: 'ai_provider',
      key: 'ai_provider',
      width: 100,
      render: (provider: string) => (
        <Tag color={provider && provider !== 'manual' ? 'purple' : 'default'}>
          {providerTextMap[provider] || provider || '未知'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => (
        <Text style={{ color: '#a0a0a0', fontSize: 13 }}>
          {time ? new Date(time).toLocaleString('zh-CN') : '-'}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: Article) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleOpenPreview(record)}
            style={{ color: '#1677ff' }}
          >
            查看
          </Button>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleOpenRewrite(record)}
            style={{ color: '#52c41a' }}
          >
            改写
          </Button>
          <Popconfirm
            title="确认删除？"
            description="删除后不可恢复"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <span style={{ color: '#e8e8e8' }}>
            <FileTextOutlined style={{ marginRight: 8, color: '#1677ff' }} />
            文章管理
          </span>
        }
        extra={
          <Space>
            <Button
              icon={<ImportOutlined />}
              onClick={() => setImportModalVisible(true)}
              style={{ borderColor: '#2a2a3e' }}
            >
              导入
            </Button>
            <Button
              icon={<ExportOutlined />}
              onClick={handleExport}
              style={{ borderColor: '#2a2a3e' }}
            >
              导出
            </Button>
          </Space>
        }
        style={{
          background: '#1f1f1f',
          borderColor: '#2a2a3e',
          borderRadius: 12,
        }}
        headStyle={{ borderBottom: '1px solid #2a2a3e' }}
      >
        {/* 搜索和筛选栏 */}
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={8}>
            <Input
              placeholder="搜索文章标题..."
              prefix={<SearchOutlined style={{ color: '#666' }} />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
              style={{ background: '#141414', borderColor: '#2a2a3e' }}
            />
          </Col>
          <Col xs={12} sm={4}>
            <Select
              placeholder="筛选状态"
              value={statusFilter}
              onChange={setStatusFilter}
              allowClear
              style={{ width: '100%' }}
              options={[
                { label: '草稿', value: 'draft' },
                { label: '待发布', value: 'pending' },
                { label: '已发布', value: 'published' },
                { label: '发布失败', value: 'failed' },
              ]}
            />
          </Col>
          <Col xs={12} sm={4}>
            <Select
              placeholder="筛选分类"
              value={categoryFilter}
              onChange={setCategoryFilter}
              allowClear
              style={{ width: '100%' }}
              options={categoryOptions}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Space>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleSearch}
              >
                搜索
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  setKeyword('');
                  setStatusFilter(undefined);
                  setCategoryFilter(undefined);
                  fetchArticles({ page: 1, page_size: 10 });
                }}
              >
                重置
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 批量操作 */}
        {selectedRowKeys.length > 0 && (
          <div
            style={{
              marginBottom: 16,
              padding: '8px 16px',
              background: '#141414',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <Text style={{ color: '#a0a0a0' }}>
              已选择 <span style={{ color: '#1677ff' }}>{selectedRowKeys.length}</span> 项
            </Text>
            <Popconfirm
              title={`确认删除 ${selectedRowKeys.length} 篇文章？`}
              onConfirm={handleBatchDelete}
              okText="确定"
              cancelText="取消"
            >
              <Button danger size="small" icon={<DeleteOutlined />}>
                批量删除
              </Button>
            </Popconfirm>
            <Button
              type="primary"
              size="small"
              icon={<SendOutlined />}
              onClick={() => setBatchModalVisible(true)}
            >
              批量发布
            </Button>
          </div>
        )}

        {/* 文章表格 */}
        {initialLoading ? (
          <div style={{ padding: '8px 0' }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  padding: '12px 0',
                  borderBottom: '1px solid #2a2a3e',
                }}
              >
                <Skeleton.Input active size="small" style={{ width: 16, minWidth: 16 }} />
                <Skeleton.Input active size="small" style={{ width: '40%', minWidth: 120 }} />
                <Skeleton.Input active size="small" style={{ width: 60, minWidth: 60 }} />
                <Skeleton.Input active size="small" style={{ width: 50, minWidth: 50 }} />
                <Skeleton.Input active size="small" style={{ width: 70, minWidth: 70 }} />
                <Skeleton.Input active size="small" style={{ width: 130, minWidth: 130 }} />
              </div>
            ))}
          </div>
        ) : (
          <Table
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys),
            }}
            columns={columns}
            dataSource={articles}
            rowKey="id"
            loading={loading}
            pagination={{
              current: currentPage,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 篇文章`,
              onChange: handlePageChange,
            }}
            size="middle"
          />
        )}
      </Card>

      {/* 批量发布弹窗 */}
      <Modal
        title="批量发布"
        open={batchModalVisible}
        onCancel={() => setBatchModalVisible(false)}
        onOk={handleBatchPublish}
        confirmLoading={batchPublishing}
        okText="开始发布"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <Text style={{ color: '#a0a0a0', display: 'block', marginBottom: 8 }}>
            已选择 {selectedRowKeys.length} 篇文章
          </Text>
        </div>
        <div style={{ marginBottom: 16 }}>
          <Text style={{ color: '#e8e8e8', display: 'block', marginBottom: 8 }}>选择发布账号</Text>
          <Select
            placeholder="选择账号"
            value={batchAccountId}
            onChange={setBatchAccountId}
            style={{ width: '100%' }}
            options={accounts.filter(a => a.login_status === 'logged_in').map(a => ({
              label: a.nickname || '未命名',
              value: a.id,
            }))}
          />
        </div>
        <div>
          <Text style={{ color: '#e8e8e8', display: 'block', marginBottom: 8 }}>发布间隔（分钟）</Text>
          <InputNumber
            min={5}
            max={1440}
            value={batchInterval}
            onChange={(v) => setBatchInterval(v || 10)}
            style={{ width: '100%' }}
          />
        </div>
      </Modal>

      {/* 导入文章弹窗 */}
      <Modal
        title="导入文章"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
      >
        <div style={{ padding: '16px 0' }}>
          <Text style={{ color: '#a0a0a0', display: 'block', marginBottom: 16 }}>
            支持导入 .md 和 .txt 格式文件，文章标题将从文件第一行标题或首行文字中提取。
          </Text>
          <Upload.Dragger
            accept=".md,.txt,.markdown"
            showUploadList={false}
            beforeUpload={handleImportFile}
            disabled={importLoading}
            style={{ background: '#141414', borderColor: '#2a2a3e' }}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ color: '#1677ff', fontSize: 48 }} />
            </p>
            <p className="ant-upload-text" style={{ color: '#e8e8e8' }}>
              {importLoading ? '导入中...' : '点击或拖拽文件到此区域'}
            </p>
            <p className="ant-upload-hint" style={{ color: '#666' }}>
              支持 .md / .txt / .markdown 格式
            </p>
          </Upload.Dragger>
        </div>
      </Modal>

      {/* 文章预览弹窗（含编辑模式） */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingRight: 24 }}>
            <span>{previewArticle?.title || '文章预览'}</span>
            {previewArticle && (
              <Button
                type={previewEditMode ? 'primary' : 'default'}
                size="small"
                icon={<EditOutlined />}
                onClick={handleToggleEditMode}
                style={previewEditMode ? {} : { borderColor: '#2a2a3e' }}
              >
                {previewEditMode ? '取消编辑' : '编辑'}
              </Button>
            )}
          </div>
        }
        open={!!previewArticle}
        onCancel={() => {
          setPreviewArticle(null);
          setPreviewEditMode(false);
        }}
        footer={
          previewEditMode
            ? [
                <Button
                  key="cancel"
                  onClick={() => setPreviewEditMode(false)}
                >
                  取消
                </Button>,
                <Button
                  key="save"
                  type="primary"
                  loading={editSaving}
                  onClick={handleSaveEdit}
                >
                  保存
                </Button>,
              ]
            : null
        }
        width={previewEditMode ? 900 : 700}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
      >
        {previewArticle && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Space size={[8, 8]} wrap>
                <Tag color={statusConfig[previewArticle.status]?.color}>
                  {statusConfig[previewArticle.status]?.text}
                </Tag>
                <Tag color={previewArticle.ai_provider && previewArticle.ai_provider !== 'manual' ? 'purple' : 'default'}>
                  {providerTextMap[previewArticle.ai_provider] || previewArticle.ai_provider || '未知'}
                </Tag>
                {previewArticle.category && (
                  <Tag color={categoryColorMap[previewArticle.category] || 'default'}>
                    {previewArticle.category}
                  </Tag>
                )}
                <Text type="secondary">字数: {previewArticle.word_count}</Text>
                <Text type="secondary">
                  创建: {new Date(previewArticle.created_at).toLocaleString('zh-CN')}
                </Text>
              </Space>
            </div>
            {previewArticle.tags && previewArticle.tags.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                {previewArticle.tags.map((tag, i) => (
                  <Tag key={i} color="blue">{tag}</Tag>
                ))}
              </div>
            )}
            {previewEditMode ? (
              <MarkdownEditor
                value={editContent}
                onChange={setEditContent}
                height={400}
              />
            ) : (
              <Paragraph
                style={{
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.8,
                  color: '#d0d0d0',
                }}
              >
                {previewArticle.content}
              </Paragraph>
            )}
          </div>
        )}
      </Modal>

      {/* 改写文章弹窗 */}
      <Modal
        title="改写文章"
        open={rewriteModalVisible}
        onCancel={() => {
          setRewriteModalVisible(false);
          setRewriteArticle(null);
        }}
        onOk={handleRewrite}
        confirmLoading={rewriteLoading}
        okText="开始改写"
        cancelText="取消"
      >
        {rewriteArticle && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Text style={{ color: '#e8e8e8', display: 'block', marginBottom: 4 }}>
                原文标题
              </Text>
              <Text style={{ color: '#a0a0a0' }}>
                {rewriteArticle.title}
              </Text>
              <Text style={{ color: '#666', display: 'block', fontSize: 12, marginTop: 4 }}>
                字数: {rewriteArticle.word_count} | 来源: {providerTextMap[rewriteArticle.ai_provider] || rewriteArticle.ai_provider}
              </Text>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Text style={{ color: '#e8e8e8', display: 'block', marginBottom: 8 }}>
                改写风格
              </Text>
              <Select
                value={rewriteStyle}
                onChange={setRewriteStyle}
                style={{ width: '100%' }}
                options={rewriteStyleOptions}
              />
            </div>

            <div>
              <Text style={{ color: '#e8e8e8', display: 'block', marginBottom: 8 }}>
                额外指令（可选）
              </Text>
              <Input.TextArea
                value={rewriteInstruction}
                onChange={(e) => setRewriteInstruction(e.target.value)}
                rows={3}
                placeholder="如：增加更多数据支撑、使用更多比喻、控制在800字以内..."
                maxLength={500}
                showCount
                style={{ background: '#141414', borderColor: '#2a2a3e' }}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ArticleList;
