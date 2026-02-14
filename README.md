# 知乎自动发文系统 (Zhihu Auto Publisher)

全自动 AI 内容生产 + 多账号发布的知乎运营系统。从选题到发布全链路自动化，内置反AI检测，支持每日批量生成发布。

## 核心能力

### ContentPilot 自动驾驶

系统的核心模块。配置好内容方向后，全程无需人工干预：

```
配置方向 → [定时触发] → AI 自动选题 → 内容去重 → AI 生成文章 → 自动入库 → 定时发布
     ↑ 一次性配置                    ↓ 以下全部自动运行 ↓
```

- 每30分钟自动扫描所有启用方向，在活跃时段（8:00-23:00）持续生成
- 每个方向可独立配置：每日生成数量、AI提供商、写作风格、发布账号
- 智能选题去重：基于哈希校验，自动排除已生成的相似主题
- 生成后自动加入发布队列，按配置间隔依次发布

### 反AI检测

四级可调的反AI检测系统，从 prompt 层面解决 AI 内容识别问题：

| 等级 | 策略 |
|------|------|
| 0 - 关闭 | 不做处理 |
| 1 - 轻度 | 避免常见AI套话 |
| 2 - 中度 | 口语化表达 + 案例穿插 |
| 3 - 强力 | 全面拟人化：禁用AI词表、强制个人化叙述、不确定表达、段落长度随机化、行业黑话 |

强力模式下的具体措施：
- **禁用词表**：然而、不禁、值得一提的是、毫无疑问、与此同时、综上所述等20+个AI高频词
- **强制特征**：口语化过渡词、"个人经历"案例、不确定表达、跑题与拉回、自嘲式表达
- **结构打乱**：段落长度随机变化、句式长短交替、感叹句/反问句穿插
- **细节伪装**：模糊化数据引用、具体时间替代模糊时间、行业黑话和圈内梗

### AI 文章生成

四种生成模式，覆盖不同内容场景：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 单篇生成 | 输入主题，直接生成一篇文章 | 快速产出 |
| 系列生成 | 自动规划大纲，批量生成关联文章 | 专栏连载 |
| 智能体 (Agent) | 分析参考文章 → 规划选题 → 批量生成 | 竞品分析、差异化内容 |
| 故事模式 | 五阶段流水线：素材提取 → 故事规划 → 章节撰写 → 组装 → 去AI润色 | 知乎盐选故事 |

### 多AI提供商

支持9个AI提供商，智能自动切换：

| 提供商 | 模型 | 环境变量前缀 |
|--------|------|-------------|
| Google Gemini | gemini-2.5-flash / 3-pro | `GEMINI_` |
| GPT-5 Codex | gpt-5-codex (Responses API) | `CODEX_` |
| OpenAI | gpt-5.1 | `OPENAI_` |
| Claude | claude-sonnet-4.5 | `CLAUDE_` |
| DeepSeek | deepseek-chat | `DEEPSEEK_` |
| 通义千问 | qwen3-max | `QWEN_` |
| 智谱GLM | glm-5 | `ZHIPU_` |
| Moonshot | kimi-k2.5 | `MOONSHOT_` |
| 豆包 | doubao-seed | `DOUBAO_` |

通过 `DEFAULT_AI_PROVIDER` 配置默认提供商，设为 `auto` 时自动选择第一个已配置的提供商。

### 自动化发布

- Playwright 浏览器自动化，持久化登录状态
- 反检测：浏览器指纹伪装、UA轮换、人类行为模拟、随机操作延迟
- 多账号管理：Cookie/二维码登录、独立浏览器Profile
- 发布控制：每日限额、最小间隔、活跃时间窗口
- 失败重试：指数退避策略（60s基础延迟，最大30分钟）
- 批量发布：可配置间隔，自动添加 ±5分钟随机抖动

### 数据与监控

- 仪表盘：文章总数、发布成功率、账号状态一览
- 任务调度：日历视图、列表视图、最佳发布时段推荐
- 发布历史：详细记录、截图保存、CSV导出
- SSE 实时通知：发布成功/失败即时推送

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite 5 + Ant Design 5 + Zustand |
| 后端 | Python 3.10+ + FastAPI + Uvicorn + SQLAlchemy 2.0 (async) |
| 数据库 | SQLite (aiosqlite) |
| 调度器 | APScheduler (AsyncIOScheduler) |
| 浏览器自动化 | Playwright (Chromium) |
| 实时通信 | Server-Sent Events (SSE) |

## 项目结构

```
zhihudenglu/
├── frontend/                    # React 前端
│   └── src/
│       ├── pages/
│       │   ├── ContentPilot/    # 自动驾驶管理
│       │   ├── ArticleGenerate/ # AI 文章生成（4种模式）
│       │   ├── ArticleList/     # 文章管理
│       │   ├── AccountManage/   # 账号管理
│       │   ├── TaskSchedule/    # 任务调度（日历/列表）
│       │   ├── PublishHistory/  # 发布历史
│       │   ├── Dashboard/       # 仪表盘
│       │   └── Settings/        # 系统设置
│       ├── services/api.ts      # API 请求层
│       ├── stores/              # Zustand 状态管理
│       └── components/          # 通用组件（Layout、通知中心）
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                 # API 路由
│   │   │   ├── pilot.py         # 自动驾驶 API（14个端点）
│   │   │   ├── articles.py      # 文章 API
│   │   │   ├── publish.py       # 发布 API
│   │   │   ├── accounts.py      # 账号 API
│   │   │   ├── tasks.py         # 任务 API
│   │   │   ├── settings.py      # 设置 API
│   │   │   └── events.py        # SSE 事件流
│   │   ├── core/                # 核心业务逻辑
│   │   │   ├── content_pilot.py # ContentPilot 自动驾驶引擎
│   │   │   ├── ai_generator.py  # AI 生成调度器
│   │   │   ├── ai_providers/    # 9个 AI 提供商适配器
│   │   │   ├── article_agent.py # 智能体（分析→规划→生成）
│   │   │   ├── story_agent.py   # 故事生成（5阶段流水线）
│   │   │   ├── task_scheduler.py# APScheduler 任务调度
│   │   │   ├── zhihu_publisher.py # 知乎发布器
│   │   │   └── zhihu_auth.py    # 知乎登录认证
│   │   ├── models/              # SQLAlchemy 数据模型
│   │   │   ├── pilot.py         # ContentDirection + GeneratedTopic
│   │   │   ├── article.py       # Article
│   │   │   ├── task.py          # PublishTask + PublishRecord
│   │   │   └── account.py       # Account
│   │   ├── automation/          # 浏览器自动化（反检测）
│   │   └── database/            # 数据库连接
│   └── .env                     # 环境变量（不提交到Git）
└── README.md
```

## 快速开始

### 环境要求

- Node.js >= 18
- Python >= 3.10
- 至少一个 AI 提供商的 API Key

### 安装

```bash
# 克隆项目
git clone https://gitee.com/yunqin1996/zhihudenglu.git
cd zhihudenglu

# 安装前后端依赖
npm run install:all

# 安装 Playwright 浏览器
npm run setup

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 API Key
```

### 启动

```bash
# 同时启动前后端
npm run dev

# 或分别启动
npm run dev:frontend   # 前端: http://localhost:5173
npm run dev:backend    # 后端: http://localhost:18901
```

访问 http://localhost:5173 使用系统，API 文档在 http://localhost:18901/docs

### 使用 ContentPilot 自动驾驶

1. 进入「自动驾驶」页面
2. 点击「新建方向」，配置内容方向（名称、关键词、风格、每日数量等）
3. 设置反AI检测强度（建议选择「强力」）
4. 开启「自动发布」并选择发布账号
5. 点击启动按钮，系统开始全自动运行

## 环境变量

### AI 提供商配置

```bash
# 默认提供商（auto / gemini / codex / openai / claude 等）
DEFAULT_AI_PROVIDER=gemini

# 至少配置一个提供商的 API Key
# 每个提供商需要三个变量：{PREFIX}API_KEY、{PREFIX}BASE_URL、{PREFIX}MODEL

GEMINI_API_KEY=your_key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
GEMINI_MODEL=gemini-2.5-flash

CODEX_API_KEY=your_key
CODEX_BASE_URL=https://api.openai.com/openai
CODEX_MODEL=gpt-5-codex
```

### 发布控制

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DAILY_PUBLISH_LIMIT` | 单账号每日发布上限 | 5 |
| `MIN_PUBLISH_INTERVAL` | 最小发布间隔（秒） | 300 |
| `ACTIVE_TIME_START` | 活跃时间开始（时） | 8 |
| `ACTIVE_TIME_END` | 活跃时间结束（时） | 23 |
| `MAX_RETRY_COUNT` | 失败最大重试次数 | 3 |
| `BROWSER_HEADLESS` | 无头浏览器模式 | false |

## API 接口

### ContentPilot 自动驾驶

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/pilot/status` | GET | 自动驾驶状态 |
| `/api/pilot/directions` | GET/POST | 方向列表/创建 |
| `/api/pilot/directions/{id}` | PUT/DELETE | 更新/删除方向 |
| `/api/pilot/directions/{id}/toggle` | POST | 启用/停用方向 |
| `/api/pilot/run/{id}` | POST | 手动触发单个方向 |
| `/api/pilot/run-all` | POST | 触发所有方向 |
| `/api/pilot/directions/{id}/topics` | GET | 查看已生成主题 |

### 文章生成

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/articles/generate` | POST | 单篇生成 |
| `/api/articles/generate-stream` | POST | 流式生成（SSE） |
| `/api/articles/series-outline` | POST | 系列大纲 |
| `/api/articles/series-generate` | POST | 批量生成系列 |
| `/api/articles/agent-generate` | POST | 智能体生成 |
| `/api/articles/story-generate` | POST | 故事生成 |
| `/api/articles/rewrite` | POST | 改写文章 |

### 其他

| 端点 | 说明 |
|------|------|
| `/api/accounts/*` | 账号管理（CRUD、登录、Cookie导入） |
| `/api/publish/*` | 发布管理（立即/定时/批量发布） |
| `/api/tasks/*` | 任务调度（列表/日历/导出） |
| `/api/settings` | 系统设置（AI配置/发布策略/浏览器配置） |
| `/api/stats/*` | 数据统计（仪表盘/时段分布/最佳时段） |
| `/api/events/stream` | SSE 实时事件流 |

## 许可证

本项目仅供学习交流使用。请遵守知乎社区规范和相关法律法规。
