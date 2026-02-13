import { create } from 'zustand';
import { settingsAPI } from '../services/api';
import type { Settings } from '../utils/types';

// ============================================================
// 默认设置值
// ============================================================

const defaultSettings: Settings = {
  ai_config: {
    provider: 'openai',
    api_key: '',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-5.2',
    temperature: 0.7,
    max_tokens: 4096,
  },
  publish_strategy: {
    default_mode: 'immediate',
    interval_minutes: 5,
    max_retries: 3,
    retry_delay_seconds: 60,
    daily_limit: 20,
  },
  browser_config: {
    headless: true,
    launch_timeout: 30000,
    action_timeout: 15000,
    user_agent: '',
    proxy: '',
  },
};

// ============================================================
// Store 接口定义
// ============================================================

interface SettingsStore {
  /** 当前设置 */
  settings: Settings;
  /** 是否正在加载 */
  loading: boolean;
  /** 是否正在保存 */
  saving: boolean;
  /** 设置是否已修改（脏标记） */
  dirty: boolean;
  /** 错误信息 */
  error: string | null;

  // Actions
  fetchSettings: () => Promise<void>;
  updateSettings: (data: Partial<Settings>) => Promise<void>;
  /** 本地修改设置（不提交到服务器，用于表单编辑） */
  setLocalSettings: (data: Partial<Settings>) => void;
  /** 重置为服务器端的设置 */
  resetSettings: () => Promise<void>;
  clearError: () => void;
}

// ============================================================
// Store 实现
// ============================================================

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: defaultSettings,
  loading: false,
  saving: false,
  dirty: false,
  error: null,

  /** 从服务器获取设置 */
  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const response = await settingsAPI.get();
      set({
        settings: response.data,
        loading: false,
        dirty: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取设置失败';
      set({ loading: false, error: message });
      throw error;
    }
  },

  /** 提交设置到服务器 */
  updateSettings: async (data: Partial<Settings>) => {
    set({ saving: true, error: null });
    try {
      // 将局部更新合并到当前设置
      const currentSettings = get().settings;
      const mergedSettings: Settings = {
        ai_config: { ...currentSettings.ai_config, ...data.ai_config },
        publish_strategy: { ...currentSettings.publish_strategy, ...data.publish_strategy },
        browser_config: { ...currentSettings.browser_config, ...data.browser_config },
      };

      const response = await settingsAPI.update(mergedSettings);
      set({
        settings: response.data,
        saving: false,
        dirty: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '保存设置失败';
      set({ saving: false, error: message });
      throw error;
    }
  },

  /** 本地编辑设置（标记脏状态） */
  setLocalSettings: (data: Partial<Settings>) => {
    const currentSettings = get().settings;
    set({
      settings: {
        ai_config: { ...currentSettings.ai_config, ...data.ai_config },
        publish_strategy: { ...currentSettings.publish_strategy, ...data.publish_strategy },
        browser_config: { ...currentSettings.browser_config, ...data.browser_config },
      },
      dirty: true,
    });
  },

  /** 重置设置（从服务器重新获取） */
  resetSettings: async () => {
    await get().fetchSettings();
  },

  /** 清除错误信息 */
  clearError: () => {
    set({ error: null });
  },
}));
