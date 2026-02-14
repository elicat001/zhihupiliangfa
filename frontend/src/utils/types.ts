// ============================================================
// 文章相关类型
// ============================================================

/** AI生成文章的请求参数 */
export interface GenerateParams {
  /** 文章主题/关键词 */
  topic: string;
  /** 文章风格：professional-专业、casual-轻松、humorous-幽默、academic-学术 */
  style: 'professional' | 'casual' | 'humorous' | 'academic';
  /** 目标字数 */
  word_count: number;
  /** AI 提供商：openai / deepseek / claude */
  ai_provider?: string;
  /** 是否启用 AI 配图 */
  enable_images?: boolean;
}

/** AI生成的文章（尚未保存到数据库） */
export interface GeneratedArticle {
  title: string;
  content: string;
  summary: string;
  tags: string[];
  word_count: number;
}

/** 文章状态 */
export type ArticleStatus = 'draft' | 'pending' | 'published' | 'failed';

/** 已保存的文章 */
export interface Article {
  id: number;
  title: string;
  content: string;
  summary: string;
  tags: string[];
  word_count: number;
  /** AI 提供商 */
  ai_provider: string;
  status: ArticleStatus;
  created_at: string;
  /** 图片元数据 */
  images?: Record<string, unknown> | null;
  /** 文章分类 */
  category?: string | null;
  /** 系列文章 UUID */
  series_id?: string | null;
  /** 系列中的顺序 */
  series_order?: number | null;
  /** 系列标题 */
  series_title?: string | null;
}

// ============================================================
// 系列文章相关类型
// ============================================================

/** 系列大纲请求参数 */
export interface SeriesOutlineParams {
  topic: string;
  count: number;
  ai_provider: string;
}

/** 系列大纲中的单篇文章 */
export interface SeriesOutlineArticle {
  order: number;
  title: string;
  description: string;
  key_points: string[];
}

/** 系列大纲响应 */
export interface SeriesOutlineResponse {
  series_title: string;
  description: string;
  articles: SeriesOutlineArticle[];
}

/** 系列文章批量生成请求参数 */
export interface SeriesGenerateParams {
  series_title: string;
  articles: Array<{
    title: string;
    description: string;
    key_points: string[];
  }>;
  style: string;
  word_count: number;
  ai_provider: string;
}

/** 文章改写请求参数 */
export interface ArticleRewriteParams {
  article_id: number;
  style: string;
  instruction?: string;
}

/** 智能体生成请求参数 */
export interface AgentGenerateParams {
  article_ids: number[];
  count: number;
  style?: string;
  word_count: number;
  ai_provider: string;
}

/** 故事生成请求参数 */
export interface StoryGenerateParams {
  /** 参考素材原文 */
  reference_text: string;
  /** 可选的参考文章ID */
  reference_article_ids?: number[];
  /** 章节数量（3-8） */
  chapter_count: number;
  /** 总目标字数（8000-25000） */
  total_word_count: number;
  /** 故事类型 */
  story_type: 'corruption' | 'historical' | 'suspense' | 'romance' | 'workplace';
  /** AI 提供商 */
  ai_provider: string;
}

// ============================================================
// 账号相关类型
// ============================================================

/** 账号登录状态 */
export type AccountLoginStatus = 'logged_in' | 'logged_out' | 'expired' | 'checking';

/** 知乎账号 */
export interface Account {
  id: number;
  /** 知乎昵称 */
  nickname: string;
  /** 知乎UID */
  zhihu_uid: string;
  /** 是否启用 */
  is_active: boolean;
  /** 登录状态 */
  login_status: AccountLoginStatus;
  /** 每日发布上限 */
  daily_limit: number;
  /** 创建时间 */
  created_at: string;
}

/** 二维码登录响应 */
export interface QrcodeLoginResponse {
  /** base64编码的二维码图片 */
  qrcode_base64: string;
  /** 消息 */
  message: string;
}

/** 登录检查响应 */
export interface LoginCheckResponse {
  is_logged_in: boolean;
  nickname: string | null;
  message: string;
}

// ============================================================
// 发布任务相关类型
// ============================================================

/** 任务状态 */
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled';

/** 发布任务（匹配后端 TaskResponse） */
export interface PublishTask {
  id: number;
  /** 关联的文章ID */
  article_id: number;
  /** 关联的账号ID */
  account_id: number;
  /** 任务状态 */
  status: TaskStatus;
  /** 计划执行时间（定时发布） */
  scheduled_at: string | null;
  /** 重试次数 */
  retry_count: number;
  /** 失败原因 */
  error_message: string | null;
  created_at: string;
  /** 关联的文章标题 */
  article_title: string | null;
  /** 关联的账号昵称 */
  account_nickname: string | null;
}

/** 立即发布请求参数 */
export interface PublishNowParams {
  article_id: number;
  account_id: number;
}

/** 定时发布请求参数 */
export interface SchedulePublishParams {
  article_id: number;
  account_id: number;
  scheduled_at: string;
}

/** 批量发布请求参数（匹配后端 PublishBatchRequest） */
export interface BatchPublishParams {
  article_ids: number[];
  account_id: number;
  /** 每篇发布间隔（分钟），默认10 */
  interval_minutes?: number;
}

// ============================================================
// 统计仪表盘类型
// ============================================================

/** 仪表盘统计数据 (匹配后端 DashboardStats) */
export interface DashboardStats {
  /** 文章总数 */
  total_articles: number;
  /** 草稿文章数 */
  draft_articles: number;
  /** 已发布文章数 */
  published_articles: number;
  /** 账号总数 */
  total_accounts: number;
  /** 活跃账号数 */
  active_accounts: number;
  /** 已登录账号数 */
  logged_in_accounts: number;
  /** 总任务数 */
  total_tasks: number;
  /** 待执行任务数 */
  pending_tasks: number;
  /** 运行中任务数 */
  running_tasks: number;
  /** 成功任务数 */
  success_tasks: number;
  /** 失败任务数 */
  failed_tasks: number;
  /** 今日发布数 */
  today_published: number;
  /** 今日生成数 */
  today_generated: number;
}

/** 最近发布记录 */
export interface RecentRecord {
  id: number;
  article_title: string;
  account_nickname: string;
  status: string;
  created_at: string;
}

/** 每日趋势数据 */
export interface WeeklyTrendItem {
  date: string;
  count: number;
}

// ============================================================
// 内容模板相关类型
// ============================================================

/** Prompt 模板 */
export interface PromptTemplate {
  id: number;
  /** 模板名称 */
  name: string;
  /** 模板描述 */
  description: string;
  /** 系统提示词 */
  system_prompt: string;
  /** 用户提示词模板，支持 {topic}, {style}, {word_count} 占位符 */
  user_prompt_template: string;
  /** 默认写作风格 */
  default_style: string;
  /** 默认目标字数 */
  default_word_count: number;
  /** 是否为内置模板 */
  is_builtin: boolean;
  /** 创建时间 */
  created_at: string;
}

/** 创建模板请求参数 */
export interface TemplateCreateParams {
  name: string;
  description?: string;
  system_prompt: string;
  user_prompt_template: string;
  default_style?: string;
  default_word_count?: number;
}

/** 更新模板请求参数 */
export interface TemplateUpdateParams {
  name?: string;
  description?: string;
  system_prompt?: string;
  user_prompt_template?: string;
  default_style?: string;
  default_word_count?: number;
}

// ============================================================
// 设置相关类型
// ============================================================

/** AI配置 */
export interface AIConfig {
  /** AI服务提供商：openai、zhipu、deepseek等 */
  provider: string;
  /** API密钥 */
  api_key: string;
  /** API基础地址 */
  base_url: string;
  /** 模型名称 */
  model: string;
  /** 温度参数 */
  temperature: number;
  /** 最大token数 */
  max_tokens: number;
}

/** 发布策略配置 */
export interface PublishStrategy {
  /** 默认发布方式 */
  default_mode: 'immediate' | 'scheduled';
  /** 发布间隔（分钟） */
  interval_minutes: number;
  /** 失败后最大重试次数 */
  max_retries: number;
  /** 重试间隔（秒） */
  retry_delay_seconds: number;
  /** 每日最大发布数量（防止被风控） */
  daily_limit: number;
}

/** 浏览器配置 */
export interface BrowserConfig {
  /** 是否使用无头模式 */
  headless: boolean;
  /** 浏览器启动超时（毫秒） */
  launch_timeout: number;
  /** 页面操作超时（毫秒） */
  action_timeout: number;
  /** 自定义User-Agent */
  user_agent: string;
  /** 代理服务器地址 */
  proxy: string;
}

/** 完整设置 */
export interface Settings {
  ai_config: AIConfig;
  publish_strategy: PublishStrategy;
  browser_config: BrowserConfig;
}

// ============================================================
// API通用响应类型
// ============================================================

/** 通用API响应包装 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

/** 分页参数 */
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================================
// ContentPilot 自动驾驶类型
// ============================================================

/** 内容方向 */
export interface ContentDirection {
  id: number;
  name: string;
  description: string;
  keywords: string[];
  seed_text: string;
  ai_provider: string | null;
  generation_mode: 'single' | 'agent' | 'story';
  style: string;
  word_count: number;
  daily_count: number;
  is_active: boolean;
  auto_publish: boolean;
  publish_account_id: number | null;
  publish_interval: number;
  today_generated: number;
  anti_ai_level: number;
  schedule_start: string | null;
  schedule_end: string | null;
  schedule_days: number | null;
  created_at: string | null;
  updated_at: string | null;
  total_generated: number;
}

/** 创建/更新方向请求 */
export interface DirectionFormData {
  name: string;
  description?: string;
  keywords?: string[];
  seed_text?: string;
  ai_provider?: string | null;
  generation_mode?: string;
  style?: string;
  word_count?: number;
  daily_count?: number;
  is_active?: boolean;
  auto_publish?: boolean;
  publish_account_id?: number | null;
  publish_interval?: number;
  anti_ai_level?: number;
  schedule_start?: string | null;
  schedule_end?: string | null;
  schedule_days?: number | null;
}

/** 自动驾驶状态 */
export interface PilotStatus {
  is_running: boolean;
  active_directions: number;
  total_directions: number;
  today_total_generated: number;
}

/** 已生成主题 */
export interface GeneratedTopicItem {
  id: number;
  topic: string;
  article_id: number | null;
  created_at: string | null;
}

/** 文章列表查询参数 */
export interface ArticleListParams extends PaginationParams {
  status?: ArticleStatus;
  keyword?: string;
  category?: string;
}

/** 任务列表查询参数 */
export interface TaskListParams extends PaginationParams {
  status?: TaskStatus;
  article_id?: number;
  account_id?: number;
  start_date?: string;
  end_date?: string;
}
