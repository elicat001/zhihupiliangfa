import { create } from 'zustand';
import { articleAPI } from '../services/api';
import type {
  Article,
  GeneratedArticle,
  GenerateParams,
  ArticleListParams,
  PaginatedResponse,
} from '../utils/types';

// ============================================================
// Store 接口定义
// ============================================================

interface ArticleStore {
  /** 文章列表 */
  articles: Article[];
  /** 分页总数 */
  total: number;
  /** 当前页码 */
  currentPage: number;
  /** 每页数量 */
  pageSize: number;
  /** 是否正在加载列表 */
  loading: boolean;
  /** 是否正在生成文章 */
  generating: boolean;
  /** AI生成的文章（临时，尚未保存） */
  generatedArticle: GeneratedArticle | null;
  /** 当前选中/查看的文章 */
  currentArticle: Article | null;
  /** 错误信息 */
  error: string | null;

  // Actions
  fetchArticles: (params?: ArticleListParams) => Promise<void>;
  fetchArticleById: (id: number) => Promise<void>;
  generateArticle: (params: GenerateParams) => Promise<void>;
  saveArticle: (article: Partial<Article>) => Promise<void>;
  updateArticle: (id: number, data: Partial<Article>) => Promise<void>;
  deleteArticle: (id: number) => Promise<void>;
  batchDeleteArticles: (ids: number[]) => Promise<void>;
  clearGenerated: () => void;
  clearError: () => void;
}

// ============================================================
// Store 实现
// ============================================================

export const useArticleStore = create<ArticleStore>((set, get) => ({
  articles: [],
  total: 0,
  currentPage: 1,
  pageSize: 10,
  loading: false,
  generating: false,
  generatedArticle: null,
  currentArticle: null,
  error: null,

  /** 获取文章列表 */
  fetchArticles: async (params?: ArticleListParams) => {
    set({ loading: true, error: null });
    try {
      const response = await articleAPI.list(params);
      // 后端返回 { total, items }
      const { total, items } = response.data;
      set({
        articles: items || [],
        total: total || 0,
        currentPage: params?.page || 1,
        pageSize: params?.page_size || 10,
        loading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取文章列表失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 根据ID获取文章详情 */
  fetchArticleById: async (id: number) => {
    set({ loading: true, error: null });
    try {
      const response = await articleAPI.getById(id);
      set({ currentArticle: response.data, loading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取文章详情失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** AI生成文章 */
  generateArticle: async (params: GenerateParams) => {
    set({ generating: true, generatedArticle: null, error: null });
    try {
      const response = await articleAPI.generate(params);
      set({ generatedArticle: response.data, generating: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'AI生成文章失败';
      set({ generating: false, error: message });
      throw error;
    }
  },

  /** 保存文章（新建） */
  saveArticle: async (article: Partial<Article>) => {
    set({ loading: true, error: null });
    try {
      const response = await articleAPI.create(article);
      const newArticle = response.data;
      set((state) => ({
        articles: [newArticle, ...state.articles],
        total: state.total + 1,
        loading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '保存文章失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 更新文章 */
  updateArticle: async (id: number, data: Partial<Article>) => {
    set({ loading: true, error: null });
    try {
      const response = await articleAPI.update(id, data);
      const updatedArticle = response.data;
      set((state) => ({
        articles: state.articles.map((a) => (a.id === id ? updatedArticle : a)),
        currentArticle: state.currentArticle?.id === id ? updatedArticle : state.currentArticle,
        loading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '更新文章失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 删除文章 */
  deleteArticle: async (id: number) => {
    set({ loading: true, error: null });
    try {
      await articleAPI.delete(id);
      set((state) => ({
        articles: state.articles.filter((a) => a.id !== id),
        total: state.total - 1,
        currentArticle: state.currentArticle?.id === id ? null : state.currentArticle,
        loading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '删除文章失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 批量删除文章 */
  batchDeleteArticles: async (ids: number[]) => {
    set({ loading: true, error: null });
    try {
      await articleAPI.batchDelete(ids);
      set((state) => ({
        articles: state.articles.filter((a) => !ids.includes(a.id)),
        total: state.total - ids.length,
        loading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '批量删除失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 清除已生成的文章 */
  clearGenerated: () => {
    set({ generatedArticle: null });
  },

  /** 清除错误信息 */
  clearError: () => {
    set({ error: null });
  },
}));
