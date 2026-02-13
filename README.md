# 知乎自动发布工具 (Zhihu Auto Publisher)

一款支持 AI 智能生成文章、多账号管理、定时发布的知乎自动化运营工具。

## 功能特性

- **AI 文章生成** — 支持多种风格（专业、故事、教程、争议性等），自动生成符合知乎排版的高质量文章
- **故事创作** — 知乎盐选风格故事生成，五阶段流水线（素材提取 → 故事规划 → 章节撰写 → 组装润色 → 去AI痕迹）
- **系列文章** — 自动规划系列大纲，批量生成关联文章
- **AI 配图** — 基于文章内容自动生成/搜索配图（Gemini / Unsplash）
- **多账号管理** — 支持添加多个知乎账号，独立管理 Cookie 和发布状态
- **定时发布** — 可配置每日发布数量、时间窗口、发布间隔
- **反检测** — 浏览器指纹伪装，模拟真人操作行为
- **数据统计** — 发布记录、文章分析、运营数据可视化
- **通知系统** — 发布成功/失败实时通知（SSE 实时推送）

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Ant Design |
| 后端 | Python 3.10+ + FastAPI + Uvicorn + SQLAlchemy |
| 数据库 | SQLite |
| 浏览器自动化 | Playwright |
| AI 提供商 | OpenAI / DeepSeek / Claude / Gemini / 通义千问 / 智谱GLM / Moonshot / 豆包 |

## 项目结构

```
zhihudenglu/
├── frontend/                # 前端项目
│   ├── src/
│   │   ├── pages/           # 页面组件（文章生成、设置、发布等）
│   │   ├── components/      # 通用组件（通知中心等）
│   │   ├── services/        # API 请求封装
│   │   └── hooks/           # 自定义 Hooks
│   └── vite.config.ts
├── backend/                 # 后端项目
│   ├── app/
│   │   ├── api/             # API 路由（文章、账号、发布、统计等）
│   │   ├── core/            # 核心逻辑
│   │   │   ├── ai_generator.py        # AI 生成调度器
│   │   │   ├── ai_providers/          # 多 AI 提供商适配器
│   │   │   ├── story_agent.py         # 故事生成 Agent
│   │   │   ├── article_agent.py       # 文章规划 Agent
│   │   │   ├── image_service.py       # AI 配图服务
│   │   │   ├── zhihu_publisher.py     # 知乎发布器
│   │   │   ├── zhihu_auth.py          # 知乎登录认证
│   │   │   └── task_scheduler.py      # 定时任务调度
│   │   ├── models/          # 数据库模型
│   │   ├── schemas/         # Pydantic 数据模型
│   │   ├── automation/      # 浏览器自动化（反检测、指纹伪装）
│   │   └── database/        # 数据库连接
│   ├── prompts/             # Prompt 模板
│   ├── .env.example         # 环境变量示例
│   └── run.py               # 后端入口
├── scripts/                 # 工具脚本
└── package.json             # 项目根配置
```

## 快速开始

### 环境要求

- Node.js >= 18
- Python >= 3.10
- 至少一个 AI 提供商的 API Key

### 安装

```bash
# 1. 克隆项目
git clone https://gitee.com/yunqin1996/zhihudenglu.git
cd zhihudenglu

# 2. 安装依赖
npm run install:all

# 3. 安装浏览器（Playwright Chromium）
npm run setup

# 4. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的 API Key
```

### 启动

```bash
# 同时启动前后端
npm run dev

# 或分别启动
npm run dev:frontend   # 前端: http://localhost:5173
npm run dev:backend    # 后端: http://localhost:18900
```

启动后访问 http://localhost:5173 即可使用。

API 文档：http://localhost:18900/docs

## 配置说明

在 `backend/.env` 中配置以下内容：

### AI 提供商（至少配置一个）

| 提供商 | 环境变量前缀 | 默认模型 |
|--------|-------------|---------|
| OpenAI | `OPENAI_` | gpt-4o |
| DeepSeek | `DEEPSEEK_` | deepseek-chat |
| Claude | `CLAUDE_` | claude-sonnet-4-20250514 |
| Gemini | `GEMINI_` | gemini-2.5-flash |
| 通义千问 | `QWEN_` | qwen-plus |
| 智谱GLM | `ZHIPU_` | glm-4-flash |
| Moonshot | `MOONSHOT_` | moonshot-v1-8k |
| 豆包 | `DOUBAO_` | doubao-pro-32k |

每个提供商需配置三个变量：`{PREFIX}API_KEY`、`{PREFIX}BASE_URL`、`{PREFIX}MODEL`

### 发布控制

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DAILY_PUBLISH_LIMIT` | 每日发布上限 | 5 |
| `MIN_PUBLISH_INTERVAL` | 最小发布间隔（秒） | 300 |
| `ACTIVE_TIME_START` | 活跃时间开始（时） | 8 |
| `ACTIVE_TIME_END` | 活跃时间结束（时） | 23 |
| `BROWSER_HEADLESS` | 无头浏览器模式 | false |

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/articles/generate` | POST | 生成文章 |
| `/api/articles/generate-stream` | POST | 流式生成文章（SSE） |
| `/api/articles/story-generate` | POST | 生成知乎盐选故事 |
| `/api/articles/series-outline` | POST | 生成系列文章大纲 |
| `/api/articles/series-generate` | POST | 批量生成系列文章 |
| `/api/articles/rewrite` | POST | 改写文章 |
| `/api/accounts/*` | - | 账号管理 |
| `/api/publish/*` | - | 发布管理 |
| `/api/settings/*` | - | 系统设置 |
| `/api/stats/*` | - | 数据统计 |

## 许可证

本项目仅供学习交流使用。请遵守知乎社区规范和相关法律法规。
