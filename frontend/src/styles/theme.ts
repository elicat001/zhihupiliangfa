/**
 * Design Token System
 * Centralized design tokens for the entire application
 */

// ==================== Color Palette ====================

export const colors = {
  // Primary gradient
  primary: '#1677ff',
  primaryLight: '#4096ff',
  primaryDark: '#0958d9',

  // Accent gradient (blue → purple)
  accent: '#722ed1',
  accentLight: '#9254de',

  // Semantic colors
  success: '#52c41a',
  successLight: '#73d13d',
  warning: '#faad14',
  warningLight: '#ffc53d',
  error: '#ff4d4f',
  errorLight: '#ff7875',
  info: '#1677ff',

  // Background layers (dark → light)
  bgBase: '#0a0a14',
  bgLayout: '#101020',
  bgSidebar: '#0d0d1a',
  bgContainer: '#161625',
  bgElevated: '#1c1c30',
  bgHover: '#22223a',
  bgActive: '#282845',
  bgInput: '#111120',

  // Text colors
  textPrimary: '#e8e8f0',
  textSecondary: '#a0a0b8',
  textTertiary: '#6a6a80',
  textDisabled: '#4a4a5a',

  // Border colors
  border: '#2a2a45',
  borderLight: '#353555',
  borderHover: '#4040660',

  // Glassmorphism
  glassBg: 'rgba(22, 22, 42, 0.75)',
  glassBorder: 'rgba(255, 255, 255, 0.06)',
  glassShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',

  // Scrollbar
  scrollTrack: '#161625',
  scrollThumb: '#353555',
  scrollThumbHover: '#4a4a65',
} as const;

// ==================== Gradients ====================

export const gradients = {
  // Primary gradients
  primary: 'linear-gradient(135deg, #1677ff 0%, #722ed1 100%)',
  primarySoft: 'linear-gradient(135deg, rgba(22,119,255,0.15) 0%, rgba(114,46,209,0.15) 100%)',
  primaryBorder: 'linear-gradient(135deg, rgba(22,119,255,0.4) 0%, rgba(114,46,209,0.4) 100%)',

  // Sidebar
  sidebar: 'linear-gradient(180deg, #0d0d1f 0%, #0a0a18 50%, #0d0d22 100%)',
  sidebarActive: 'linear-gradient(90deg, rgba(22,119,255,0.2) 0%, transparent 100%)',

  // Status gradients
  success: 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
  warning: 'linear-gradient(135deg, #faad14 0%, #d48806 100%)',
  error: 'linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%)',
  info: 'linear-gradient(135deg, #1677ff 0%, #0958d9 100%)',

  // Card accents
  cardBlue: 'linear-gradient(135deg, rgba(22,119,255,0.12) 0%, rgba(22,119,255,0.03) 100%)',
  cardPurple: 'linear-gradient(135deg, rgba(114,46,209,0.12) 0%, rgba(114,46,209,0.03) 100%)',
  cardGreen: 'linear-gradient(135deg, rgba(82,196,26,0.12) 0%, rgba(82,196,26,0.03) 100%)',
  cardYellow: 'linear-gradient(135deg, rgba(250,173,20,0.12) 0%, rgba(250,173,20,0.03) 100%)',
  cardRed: 'linear-gradient(135deg, rgba(255,77,79,0.12) 0%, rgba(255,77,79,0.03) 100%)',

  // Glow effects
  glowBlue: '0 0 20px rgba(22,119,255,0.15), 0 0 40px rgba(22,119,255,0.05)',
  glowPurple: '0 0 20px rgba(114,46,209,0.15), 0 0 40px rgba(114,46,209,0.05)',
  glowGreen: '0 0 20px rgba(82,196,26,0.15)',
  glowYellow: '0 0 20px rgba(250,173,20,0.15)',
  glowRed: '0 0 20px rgba(255,77,79,0.15)',
} as const;

// ==================== Shadows ====================

export const shadows = {
  sm: '0 2px 8px rgba(0, 0, 0, 0.2)',
  md: '0 4px 16px rgba(0, 0, 0, 0.25)',
  lg: '0 8px 32px rgba(0, 0, 0, 0.3)',
  xl: '0 16px 48px rgba(0, 0, 0, 0.35)',
  card: '0 4px 20px rgba(0, 0, 0, 0.2), 0 0 1px rgba(255,255,255,0.05)',
  cardHover: '0 8px 30px rgba(0, 0, 0, 0.3), 0 0 1px rgba(255,255,255,0.08)',
  inner: 'inset 0 1px 4px rgba(0, 0, 0, 0.2)',
} as const;

// ==================== Spacing ====================

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

// ==================== Border Radius ====================

export const radius = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  xxl: 20,
  full: 9999,
} as const;

// ==================== Layout Dimensions ====================

export const layout = {
  sidebarWidth: 240,
  sidebarCollapsedWidth: 72,
  headerHeight: 60,
  contentPadding: 24,
  cardGap: 16,
} as const;

// ==================== Common Styles ====================

export const commonStyles = {
  // Glass card style
  glassCard: {
    background: colors.glassBg,
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    border: `1px solid ${colors.glassBorder}`,
    borderRadius: radius.lg,
    boxShadow: shadows.card,
  } as React.CSSProperties,

  // Elevated card
  card: {
    background: colors.bgContainer,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.lg,
    boxShadow: shadows.sm,
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  } as React.CSSProperties,

  // Card with hover glow
  cardHoverable: {
    background: colors.bgContainer,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.lg,
    boxShadow: shadows.sm,
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    cursor: 'pointer',
  } as React.CSSProperties,

  // Section header
  sectionHeader: {
    fontSize: 15,
    fontWeight: 600,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
    letterSpacing: '0.3px',
  } as React.CSSProperties,

  // Stat card icon wrapper
  iconWrapper: (color: string) => ({
    width: 44,
    height: 44,
    borderRadius: radius.md,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 20,
    color,
    background: `${color}15`,
    border: `1px solid ${color}25`,
  } as React.CSSProperties),

  // Page container
  pageContainer: {
    minHeight: '100%',
  } as React.CSSProperties,
} as const;

// ==================== Ant Design Theme Config ====================

import type { ThemeConfig } from 'antd';
import { theme } from 'antd';
import React from 'react';

export const antdTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    // Colors
    colorPrimary: colors.primary,
    colorSuccess: colors.success,
    colorWarning: colors.warning,
    colorError: colors.error,
    colorInfo: colors.info,

    // Backgrounds
    colorBgContainer: colors.bgContainer,
    colorBgElevated: colors.bgElevated,
    colorBgLayout: colors.bgLayout,

    // Text
    colorText: colors.textPrimary,
    colorTextSecondary: colors.textSecondary,
    colorTextTertiary: colors.textTertiary,
    colorTextDisabled: colors.textDisabled,

    // Border
    colorBorder: colors.border,
    colorBorderSecondary: colors.border,

    // Shape
    borderRadius: radius.md,
    borderRadiusLG: radius.lg,
    borderRadiusSM: radius.sm,

    // Typography
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
    fontSize: 14,

    // Motion
    motionDurationMid: '0.25s',
    motionDurationSlow: '0.35s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
  components: {
    Card: {
      colorBgContainer: colors.bgContainer,
      colorBorderSecondary: colors.border,
      borderRadiusLG: radius.lg,
      paddingLG: 20,
    },
    Table: {
      colorBgContainer: 'transparent',
      headerBg: 'rgba(22, 119, 255, 0.06)',
      headerColor: colors.textSecondary,
      rowHoverBg: 'rgba(22, 119, 255, 0.04)',
      borderColor: colors.border,
      headerBorderRadius: radius.md,
      cellPaddingBlock: 14,
      headerSplitColor: 'transparent',
    },
    Modal: {
      contentBg: colors.bgElevated,
      headerBg: colors.bgElevated,
      titleColor: colors.textPrimary,
      colorBgMask: 'rgba(0, 0, 0, 0.65)',
    },
    Input: {
      colorBgContainer: colors.bgInput,
      colorBorder: colors.border,
      activeBorderColor: colors.primary,
      hoverBorderColor: colors.borderLight,
      activeShadow: `0 0 0 2px rgba(22, 119, 255, 0.15)`,
    },
    InputNumber: {
      colorBgContainer: colors.bgInput,
      colorBorder: colors.border,
      activeBorderColor: colors.primary,
      hoverBorderColor: colors.borderLight,
    },
    Select: {
      colorBgContainer: colors.bgInput,
      colorBorder: colors.border,
      optionSelectedBg: 'rgba(22, 119, 255, 0.12)',
      optionActiveBg: 'rgba(22, 119, 255, 0.08)',
      selectorBg: colors.bgInput,
    },
    DatePicker: {
      colorBgContainer: colors.bgInput,
      colorBorder: colors.border,
    },
    Button: {
      borderRadius: radius.sm,
      controlHeight: 36,
      defaultBg: colors.bgElevated,
      defaultBorderColor: colors.border,
      defaultColor: colors.textSecondary,
    },
    Tag: {
      borderRadiusSM: 4,
    },
    Switch: {
      colorPrimary: colors.primary,
    },
    Slider: {
      trackBg: colors.primary,
      trackHoverBg: colors.primaryLight,
      railBg: colors.border,
      railHoverBg: colors.borderLight,
      handleColor: colors.primary,
    },
    Tabs: {
      colorBorderSecondary: colors.border,
      inkBarColor: colors.primary,
    },
    Form: {
      labelColor: colors.textSecondary,
    },
    Divider: {
      colorSplit: colors.border,
    },
    Menu: {
      itemBg: 'transparent',
      subMenuItemBg: 'transparent',
      darkItemBg: 'transparent',
      darkSubMenuItemBg: 'transparent',
    },
    Popover: {
      colorBgElevated: colors.bgElevated,
    },
    Tooltip: {
      colorBgSpotlight: colors.bgElevated,
    },
    Segmented: {
      itemSelectedBg: colors.bgElevated,
      trackBg: colors.bgInput,
    },
    Statistic: {
      titleFontSize: 13,
      contentFontSize: 22,
    },
    Skeleton: {
      gradientFromColor: colors.bgContainer,
      gradientToColor: colors.bgElevated,
    },
    Badge: {
      dotSize: 8,
    },
    Progress: {
      remainingColor: colors.border,
    },
    Alert: {
      colorInfoBg: 'rgba(22, 119, 255, 0.08)',
      colorInfoBorder: 'rgba(22, 119, 255, 0.2)',
      colorWarningBg: 'rgba(250, 173, 20, 0.08)',
      colorWarningBorder: 'rgba(250, 173, 20, 0.2)',
    },
  },
};
