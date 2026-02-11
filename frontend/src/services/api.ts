import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type {
  Article,
  GenerateParams,
  GeneratedArticle,
  ArticleListParams,
  Account,
  QrcodeLoginResponse,
  LoginCheckResponse,
  PublishTask,
  PublishNowParams,
  SchedulePublishParams,
  BatchPublishParams,
  TaskListParams,
  DashboardStats,
  RecentRecord,
  Settings,
  PaginatedResponse,
  PromptTemplate,
  TemplateCreateParams,
  TemplateUpdateParams,
  SeriesOutlineParams,
  SeriesOutlineResponse,
  SeriesGenerateParams,
  ArticleRewriteParams,
  AgentGenerateParams,
} from '../utils/types';

// ============================================================
// Axios 实例 & 拦截器
// ============================================================

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/** 请求拦截器：可在此注入token等 */
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 如果需要认证，可以在这里添加token
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/** 响应拦截器：统一处理错误 */
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      switch (status) {
        case 401:
          console.error('[API] 未授权，请重新登录');
          break;
        case 403:
          console.error('[API] 权限不足');
          break;
        case 404:
          console.error('[API] 资源不存在');
          break;
        case 422:
          console.error('[API] 参数验证失败:', data?.detail);
          break;
        case 500:
          console.error('[API] 服务器内部错误');
          break;
        default:
          console.error(`[API] 请求失败 (${status}):`, data?.message || '未知错误');
      }
    } else if (error.request) {
      console.error('[API] 网络错误，请检查网络连接');
    } else {
      console.error('[API] 请求配置错误:', error.message);
    }
    return Promise.reject(error);
  }
);

// ============================================================
// 文章相关 API
// ============================================================

export const articleAPI = {
  /** AI生成文章 */
  generate: (params: GenerateParams): Promise<AxiosResponse<GeneratedArticle>> =>
    api.post('/articles/generate', params),

  /** 获取文章列表（分页） */
  list: (params?: ArticleListParams): Promise<AxiosResponse<{ total: number; items: Article[] }>> =>
    api.get('/articles', { params }),

  /** 根据ID获取文章详情 */
  getById: (id: number): Promise<AxiosResponse<Article>> =>
    api.get(`/articles/${id}`),

  /** 创建文章 */
  create: (data: Partial<Article>): Promise<AxiosResponse<Article>> =>
    api.post('/articles', data),

  /** 更新文章 */
  update: (id: number, data: Partial<Article>): Promise<AxiosResponse<Article>> =>
    api.put(`/articles/${id}`, data),

  /** 删除文章 */
  delete: (id: number): Promise<AxiosResponse<unknown>> =>
    api.delete(`/articles/${id}`),

  /** 批量删除文章 */
  batchDelete: (ids: number[]): Promise<AxiosResponse<unknown>> =>
    api.post('/articles/batch-delete', { ids }),

  /**
   * AI 流式生成文章 (SSE)
   * 使用原生 fetch 而非 axios，因为 axios 不支持流式读取
   * 返回原始 Response 供调用方消费 ReadableStream
   */
  generateStream: (params: GenerateParams): Promise<Response> =>
    fetch('/api/articles/generate-stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }).then((res) => {
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: 流式生成请求失败`);
      }
      return res;
    }),

  /** 生成系列文章大纲 */
  seriesOutline: (data: SeriesOutlineParams): Promise<AxiosResponse<SeriesOutlineResponse>> =>
    api.post('/articles/series-outline', data),

  /** 批量生成系列文章 */
  seriesGenerate: (data: SeriesGenerateParams): Promise<AxiosResponse<Article[]>> =>
    api.post('/articles/series-generate', data),

  /** 改写文章 */
  rewrite: (data: ArticleRewriteParams): Promise<AxiosResponse<Article>> =>
    api.post('/articles/rewrite', data),

  /** 智能体批量生成文章 */
  agentGenerate: (data: AgentGenerateParams): Promise<AxiosResponse<Article[]>> =>
    api.post('/articles/agent-generate', data),

  /** 导入文章（从 .md / .txt 文件） */
  import: (file: File): Promise<AxiosResponse<Article>> => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/articles/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ============================================================
// 账号相关 API
// ============================================================

export const accountAPI = {
  /** 获取账号列表 - 后端返回 { total, items } */
  list: (): Promise<AxiosResponse<{ total: number; items: Account[] }>> =>
    api.get('/accounts'),

  /** 添加账号 - 后端期望 { nickname, zhihu_uid?, cookie_data?, daily_limit? } */
  create: (data: { nickname: string; zhihu_uid?: string; cookie_data?: string; daily_limit?: number }): Promise<AxiosResponse<Account>> =>
    api.post('/accounts', data),

  /** 删除账号 */
  delete: (id: number): Promise<AxiosResponse<{ message: string; id: number }>> =>
    api.delete(`/accounts/${id}`),

  /** 检查账号登录状态 - 后端返回 LoginCheckResponse */
  checkLogin: (id: number): Promise<AxiosResponse<LoginCheckResponse>> =>
    api.post(`/accounts/${id}/check-login`),

  /** 发起二维码登录 - 后端返回 QRCodeLoginResponse */
  qrcodeLogin: (id: number): Promise<AxiosResponse<QrcodeLoginResponse>> =>
    api.post(`/accounts/${id}/qrcode-login`),

  /** Cookie导入登录 - 后端路由 cookie-login, 期望 { cookie_data } */
  importCookie: (id: number, cookieData: string): Promise<AxiosResponse<LoginCheckResponse>> =>
    api.post(`/accounts/${id}/cookie-login`, { cookie_data: cookieData }),

  /** 更新账号信息 */
  update: (id: number, data: { nickname?: string; daily_limit?: number; is_active?: boolean }): Promise<AxiosResponse<Account>> =>
    api.put(`/accounts/${id}`, data),
};

// ============================================================
// 发布相关 API
// ============================================================

export const publishAPI = {
  /** 立即发布 */
  now: (data: PublishNowParams): Promise<AxiosResponse<PublishTask>> =>
    api.post('/publish/now', data),

  /** 定时发布 */
  schedule: (data: SchedulePublishParams): Promise<AxiosResponse<PublishTask>> =>
    api.post('/publish/schedule', data),

  /** 批量发布 */
  batch: (data: BatchPublishParams): Promise<AxiosResponse<PublishTask[]>> =>
    api.post('/publish/batch', data),
};

// ============================================================
// 任务相关 API
// ============================================================

export const taskAPI = {
  /** 获取任务列表（分页） */
  list: (params?: TaskListParams): Promise<AxiosResponse<{ total: number; items: PublishTask[] }>> =>
    api.get('/tasks', { params }),

  /** 取消任务 */
  cancel: (id: number): Promise<AxiosResponse<PublishTask>> =>
    api.delete(`/tasks/${id}`),

  /** 获取日历视图任务列表 */
  calendar: (start: string, end: string): Promise<AxiosResponse<PublishTask[]>> =>
    api.get('/tasks/calendar', { params: { start, end } }),

  /** 更新任务（重新调度等） */
  update: (id: number, data: { scheduled_at?: string }): Promise<AxiosResponse<unknown>> =>
    api.put(`/tasks/${id}`, data),

  /** 导出任务为CSV */
  exportCSV: (params?: { status?: string; account_id?: number; start_date?: string; end_date?: string }): Promise<AxiosResponse<Blob>> =>
    api.get('/tasks/export', { params: { format: 'csv', ...params }, responseType: 'blob' }),
};

// ============================================================
// 统计相关 API
// ============================================================

export const statsAPI = {
  /** 获取仪表盘统计数据 */
  dashboard: (): Promise<AxiosResponse<DashboardStats>> =>
    api.get('/stats/dashboard'),

  /** 获取最近发布记录 */
  recentRecords: (limit: number = 10): Promise<AxiosResponse<RecentRecord[]>> =>
    api.get('/stats/recent-records', { params: { limit } }),

  /** 获取最佳发布时间建议 */
  optimalTimes: (accountId?: number, days?: number): Promise<AxiosResponse<Array<{ hour: number; score: number; reason: string }>>> =>
    api.get('/stats/optimal-times', { params: { account_id: accountId, days } }),

  /** 获取发布时段分布 */
  hourDistribution: (accountId?: number, days?: number): Promise<AxiosResponse<Array<{ hour: number; total: number; success: number; failed: number }>>> =>
    api.get('/stats/hour-distribution', { params: { account_id: accountId, days } }),
};

// ============================================================
// 设置相关 API
// ============================================================

export const settingsAPI = {
  /** 获取当前设置 */
  get: (): Promise<AxiosResponse<Settings>> =>
    api.get('/settings'),

  /** 更新设置 */
  update: (data: Partial<Settings>): Promise<AxiosResponse<Settings>> =>
    api.put('/settings', data),
};

// ============================================================
// 内容模板相关 API
// ============================================================

export const templateAPI = {
  /** 获取所有模板 */
  list: (): Promise<AxiosResponse<PromptTemplate[]>> =>
    api.get('/templates'),

  /** 创建模板 */
  create: (data: TemplateCreateParams): Promise<AxiosResponse<PromptTemplate>> =>
    api.post('/templates', data),

  /** 更新模板 */
  update: (id: number, data: TemplateUpdateParams): Promise<AxiosResponse<PromptTemplate>> =>
    api.put(`/templates/${id}`, data),

  /** 删除模板 */
  delete: (id: number): Promise<AxiosResponse<unknown>> =>
    api.delete(`/templates/${id}`),
};

// ============================================================
// 通知相关 API
// ============================================================

export const notificationAPI = {
  /** 获取通知列表 */
  list: (params?: { page?: number; page_size?: number; is_read?: boolean }): Promise<AxiosResponse<{ total: number; items: Array<{ id: number; title: string; content: string | null; type: string; is_read: boolean; created_at: string | null }> }>> =>
    api.get('/notifications', { params }),

  /** 获取未读通知数量 */
  unreadCount: (): Promise<AxiosResponse<{ count: number }>> =>
    api.get('/notifications/unread-count'),

  /** 标记单条通知为已读 */
  markRead: (id: number): Promise<AxiosResponse<unknown>> =>
    api.put(`/notifications/${id}/read`),

  /** 标记所有通知为已读 */
  markAllRead: (): Promise<AxiosResponse<unknown>> =>
    api.put('/notifications/read-all'),
};

export default api;
