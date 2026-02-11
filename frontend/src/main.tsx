import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, theme, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';

// 暗色主题配置
const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#1677ff',
    colorBgContainer: '#1f1f1f',
    colorBgElevated: '#262626',
    colorBgLayout: '#141414',
    borderRadius: 8,
    colorText: '#e8e8e8',
    colorTextSecondary: '#a0a0a0',
  },
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider theme={darkTheme} locale={zhCN}>
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>
);
