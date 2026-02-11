import { create } from 'zustand';
import { accountAPI } from '../services/api';
import type { Account } from '../utils/types';

// ============================================================
// Store 接口定义
// ============================================================

interface AccountStore {
  /** 账号列表 */
  accounts: Account[];
  /** 是否正在加载 */
  loading: boolean;
  /** 错误信息 */
  error: string | null;
  /** 正在检查登录状态的账号ID集合 */
  checkingIds: Set<number>;
  /** 正在进行二维码登录的账号ID */
  qrcodeLoginId: number | null;

  // Actions
  fetchAccounts: () => Promise<void>;
  addAccount: (data: { nickname: string; zhihu_uid?: string; cookie_data?: string; daily_limit?: number }) => Promise<void>;
  deleteAccount: (id: number) => Promise<void>;
  checkLogin: (id: number) => Promise<boolean>;
  startQrcodeLogin: (id: number) => Promise<string>;
  importCookie: (id: number, cookie: string) => Promise<void>;
  updateAccount: (id: number, data: { nickname?: string; daily_limit?: number; is_active?: boolean }) => Promise<void>;
  clearError: () => void;
}

// ============================================================
// Store 实现
// ============================================================

export const useAccountStore = create<AccountStore>((set, get) => ({
  accounts: [],
  loading: false,
  error: null,
  checkingIds: new Set(),
  qrcodeLoginId: null,

  /** 获取账号列表 */
  fetchAccounts: async () => {
    set({ loading: true, error: null });
    try {
      const response = await accountAPI.list();
      // 后端返回 { total, items }
      set({ accounts: response.data.items || [], loading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取账号列表失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 添加账号 */
  addAccount: async (data: { nickname: string; zhihu_uid?: string; cookie_data?: string; daily_limit?: number }) => {
    set({ loading: true, error: null });
    try {
      const response = await accountAPI.create(data);
      const newAccount = response.data;
      set((state) => ({
        accounts: [...state.accounts, newAccount],
        loading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '添加账号失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 删除账号 */
  deleteAccount: async (id: number) => {
    set({ loading: true, error: null });
    try {
      await accountAPI.delete(id);
      set((state) => ({
        accounts: state.accounts.filter((a) => a.id !== id),
        loading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '删除账号失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 检查账号登录状态，返回是否已登录 */
  checkLogin: async (id: number): Promise<boolean> => {
    const { checkingIds } = get();
    const newCheckingIds = new Set(checkingIds);
    newCheckingIds.add(id);
    set({ checkingIds: newCheckingIds, error: null });

    try {
      const response = await accountAPI.checkLogin(id);
      // 后端返回 LoginCheckResponse: { is_logged_in, nickname, message }
      const { is_logged_in, nickname } = response.data;
      const login_status = is_logged_in ? 'logged_in' : 'expired';

      set((state) => {
        const updatedCheckingIds = new Set(state.checkingIds);
        updatedCheckingIds.delete(id);
        return {
          accounts: state.accounts.map((a) =>
            a.id === id
              ? { ...a, login_status: login_status as Account['login_status'], nickname: nickname || a.nickname }
              : a
          ),
          checkingIds: updatedCheckingIds,
        };
      });

      return is_logged_in;
    } catch (error: unknown) {
      const updatedCheckingIds = new Set(get().checkingIds);
      updatedCheckingIds.delete(id);
      const message = error instanceof Error ? error.message : '检查登录状态失败';
      set({ checkingIds: updatedCheckingIds, error: message });
      throw error;
    }
  },

  /** 发起二维码登录，返回二维码图片的base64字符串 */
  startQrcodeLogin: async (id: number): Promise<string> => {
    set({ qrcodeLoginId: id, error: null });
    try {
      const response = await accountAPI.qrcodeLogin(id);
      // 后端直接返回 QRCodeLoginResponse
      const { qrcode_base64 } = response.data;
      return qrcode_base64;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取登录二维码失败';
      set({ qrcodeLoginId: null, error: message });
      throw error;
    }
  },

  /** 导入Cookie登录 */
  importCookie: async (id: number, cookie: string) => {
    set({ loading: true, error: null });
    try {
      const response = await accountAPI.importCookie(id, cookie);
      // 后端返回 LoginCheckResponse: { is_logged_in, nickname, message }
      const { is_logged_in, nickname } = response.data;
      const login_status = is_logged_in ? 'logged_in' : 'expired';

      set((state) => ({
        accounts: state.accounts.map((a) =>
          a.id === id
            ? { ...a, login_status: login_status as Account['login_status'], nickname: nickname || a.nickname }
            : a
        ),
        loading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '导入Cookie失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 更新账号信息 */
  updateAccount: async (id: number, data: { nickname?: string; daily_limit?: number; is_active?: boolean }) => {
    set({ loading: true, error: null });
    try {
      const response = await accountAPI.update(id, data);
      const updated = response.data;
      set((state) => ({
        accounts: state.accounts.map((a) =>
          a.id === id ? { ...a, ...updated } : a
        ),
        loading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '更新账号失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 清除错误信息 */
  clearError: () => {
    set({ error: null });
  },
}));
