import { create } from 'zustand';
import { publishAPI, taskAPI } from '../services/api';
import type {
  PublishTask,
  TaskListParams,
  BatchPublishParams,
  SchedulePublishParams,
  PaginatedResponse,
} from '../utils/types';

// ============================================================
// Store 接口定义
// ============================================================

interface TaskStore {
  /** 任务列表 */
  tasks: PublishTask[];
  /** 分页总数 */
  total: number;
  /** 当前页码 */
  currentPage: number;
  /** 每页数量 */
  pageSize: number;
  /** 是否正在加载 */
  loading: boolean;
  /** 是否正在执行发布操作 */
  publishing: boolean;
  /** 错误信息 */
  error: string | null;

  // Actions
  fetchTasks: (params?: TaskListParams) => Promise<void>;
  publishNow: (articleId: number, accountId: number) => Promise<void>;
  schedulePublish: (params: SchedulePublishParams) => Promise<void>;
  scheduleBatch: (params: BatchPublishParams) => Promise<void>;
  cancelTask: (id: number) => Promise<void>;
  clearError: () => void;
}

// ============================================================
// Store 实现
// ============================================================

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  total: 0,
  currentPage: 1,
  pageSize: 10,
  loading: false,
  publishing: false,
  error: null,

  /** 获取任务列表 */
  fetchTasks: async (params?: TaskListParams) => {
    set({ loading: true, error: null });
    try {
      const response = await taskAPI.list(params);
      // 后端返回 { total, items }
      const { total, items } = response.data;
      set({
        tasks: items || [],
        total: total || 0,
        currentPage: params?.page || 1,
        pageSize: params?.page_size || 10,
        loading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取任务列表失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 立即发布 */
  publishNow: async (articleId: number, accountId: number) => {
    set({ publishing: true, error: null });
    try {
      const response = await publishAPI.now({
        article_id: articleId,
        account_id: accountId,
      });
      const newTask = response.data;
      set((state) => ({
        tasks: [newTask, ...state.tasks],
        total: state.total + 1,
        publishing: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '发布失败';
      set({ publishing: false, error: message });
      throw error;
    }
  },

  /** 定时发布 */
  schedulePublish: async (params: SchedulePublishParams) => {
    set({ publishing: true, error: null });
    try {
      const response = await publishAPI.schedule(params);
      const newTask = response.data;
      set((state) => ({
        tasks: [newTask, ...state.tasks],
        total: state.total + 1,
        publishing: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '创建定时任务失败';
      set({ publishing: false, error: message });
      throw error;
    }
  },

  /** 批量发布 */
  scheduleBatch: async (params: BatchPublishParams) => {
    set({ publishing: true, error: null });
    try {
      const response = await publishAPI.batch(params);
      const newTasks = response.data;
      set((state) => ({
        tasks: [...newTasks, ...state.tasks],
        total: state.total + newTasks.length,
        publishing: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '批量发布失败';
      set({ publishing: false, error: message });
      throw error;
    }
  },

  /** 取消任务 */
  cancelTask: async (id: number) => {
    set({ error: null });
    try {
      const response = await taskAPI.cancel(id);
      const cancelledTask = response.data;
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? cancelledTask : t)),
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '取消任务失败';
      set({ error: message });
      throw error;
    }
  },

  /** 清除错误信息 */
  clearError: () => {
    set({ error: null });
  },
}));
