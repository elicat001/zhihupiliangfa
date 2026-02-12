

# 知乎文章助手 (zhihudenglu)

一个基于 AI 的知乎文章管理与自动发布系统，支持 AI 生成文章、定时发布、账号管理、数据分析等功能。

## ✨ 功能特性

- **AI 智能生成**: 支持 DeepSeek、Claude、OpenAI、通义千问、月之暗面、智谱 AI、豆包 等多种 AI 提供商，一键生成专业文章。
- **批量操作**: 支持系列文章大纲生成、批量发布、批量删除。
- **防检测模拟**: 内置浏览器指纹和人类行为模拟，降低登录和发布风险。
- **任务调度**: 支持立即发布和定时发布，可视化日历视图。
- **数据统计**: 仪表盘展示发布数据，分析最佳发布时间。
- **实时通知**: Server-Sent Events (SSE) 实时推送任务状态和系统通知。
- **多账号管理**: 支持 Cookie 导入和扫码登录切换账号。

## 🛠 技术栈

- **后端**: Python 3.10+ / FastAPI / SQLAlchemy / Playwright
- **前端**: React 18 / TypeScript / Ant Design / Axios
- **数据库**: SQLite (默认) / PostgreSQL / MySQL (配置切换)
- **AI**: OpenAI 兼容 API 接口

## 📂 项目结构

```
zhihudenglu/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API 路由端点
│   │   ├── core/           # 核心逻辑 (AI生成、调度、爬虫)
│   │   ├── automation/     # 浏览器自动化 (防检测)
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic 数据模型
│   │   └── database/       # 数据库连接
│   └── requirements.txt    # Python 依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   ├── components/     # 公共组件
│   │   ├── stores/         # 状态管理 (Pinia/Zustand)
│   │   └── services/       # API 服务
│   └── package.json
└── README.md
```

## 🚀 快速开始

### 1. 环境准备

- Python 3.10+
- Node.js 18+
- Playwright (用于浏览器自动化)

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

配置环境变量 (复制 `.env.example` 为 `.env`):

```bash
# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./zhihu.db

# AI 配置 (示例)
DEEPSEEK_API_KEY=sk-xxxx
DEFAULT_AI_PROVIDER=deepseek

# 系统配置
SECRET_KEY=your-secret-key
```

### 3. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 启动服务

**后端**:
```bash
cd backend
uvicorn run:app --reload --host 0.0.0.0 --port 8000
```

**前端**:
```bash
cd frontend
npm run dev
```

访问 `http://localhost:5173` 进入应用。

## 📖 API 文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看 Swagger UI 文档。

### 主要接口模块

| 模块 | 端点前缀 | 说明 |
|------|---------|------|
| **账号管理** | `/api/accounts` | 登录状态检查、扫码登录、Cookie 登录 |
| **文章管理** | `/api/articles` | AI 生成、手动创建、导入导出、系列生成 |
| **发布任务** | `/api/publish` | 立即发布、定时发布、批量发布 |
| **任务中心** | `/api/tasks` | 任务列表、取消任务、日历视图 |
| **模板管理** | `/api/templates` | AI Prompt 模板管理 |
| **数据分析** | `/api/stats` | 仪表盘统计、最佳发布时间 |
| **实时事件** | `/api/events` | SSE 事件流 |

## ⚙️ 配置说明

在 **系统设置** 页面 (`/settings`) 可配置：

- **AI 提供商选择**: 切换不同的模型服务商。
- **发布策略**: 发布间隔、失败重试次数。
- **浏览器配置**: 是否使用隐身模式、截图设置。

## 📝 许可证

本项目仅供学习和研究使用。请遵守知乎社区规范和相关法律法规，不要滥用自动化功能。