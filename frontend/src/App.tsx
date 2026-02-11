import React, { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Spin } from 'antd';
import AppLayout from './components/Layout';

// 路由懒加载，提升首屏性能
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ArticleGenerate = lazy(() => import('./pages/ArticleGenerate'));
const ArticleList = lazy(() => import('./pages/ArticleList'));
const AccountManage = lazy(() => import('./pages/AccountManage'));
const TaskSchedule = lazy(() => import('./pages/TaskSchedule'));
const PublishHistory = lazy(() => import('./pages/PublishHistory'));
const Settings = lazy(() => import('./pages/Settings'));

/** 加载中占位组件 */
const PageLoading: React.FC = () => (
  <div
    style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '60vh',
    }}
  >
    <Spin size="large" tip="加载中..." />
  </div>
);

const App: React.FC = () => {
  return (
    <AppLayout>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/generate" element={<ArticleGenerate />} />
          <Route path="/articles" element={<ArticleList />} />
          <Route path="/accounts" element={<AccountManage />} />
          <Route path="/tasks" element={<TaskSchedule />} />
          <Route path="/history" element={<PublishHistory />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Suspense>
    </AppLayout>
  );
};

export default App;
