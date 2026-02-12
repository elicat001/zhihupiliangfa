# Zhihu Article Assistant (zhihudenglu)

An AI-powered Zhihu article management and automated publishing system featuring AI-generated articles, scheduled publishing, account management, and data analytics.

## ✨ Features

- **AI Smart Generation**: Supports multiple AI providers including DeepSeek, Claude, OpenAI, Qwen, Moonshot, Zhipu AI, and Doubao — generate professional articles with one click.
- **Bulk Operations**: Supports batch generation of article outlines, bulk publishing, and bulk deletion.
- **Anti-Detection Simulation**: Built-in browser fingerprinting and human behavior simulation to reduce risks during login and publishing.
- **Task Scheduling**: Supports immediate and scheduled publishing with a visual calendar view.
- **Data Analytics**: Dashboard displays publishing statistics and analyzes optimal publishing times.
- **Real-time Notifications**: Server-Sent Events (SSE) for real-time推送 of task status and system alerts.
- **Multi-Account Management**: Supports cookie import and QR code login for switching between accounts.

## 🛠 Technology Stack

- **Backend**: Python 3.10+ / FastAPI / SQLAlchemy / Playwright
- **Frontend**: React 18 / TypeScript / Ant Design / Axios
- **Database**: SQLite (default) / PostgreSQL / MySQL (configurable)
- **AI**: OpenAI-compatible API interface

## 📂 Project Structure

```
zhihudenglu/
├── backend/                 # Backend service
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core logic (AI generation, scheduling, crawling)
│   │   ├── automation/     # Browser automation (anti-detection)
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic data models
│   │   └── database/       # Database connection
│   └── requirements.txt    # Python dependencies
├── frontend/               # Frontend application
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable components
│   │   ├── stores/         # State management (Pinia/Zustand)
│   │   └── services/       # API services
│   └── package.json
└── README.md
```

## 🚀 Quick Start

### 1. Environment Preparation

- Python 3.10+
- Node.js 18+
- Playwright (for browser automation)

### 2. Backend Configuration

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

Configure environment variables (copy `.env.example` to `.env`):

```bash
# Database configuration
DATABASE_URL=sqlite+aiosqlite:///./zhihu.db

# AI configuration (example)
DEEPSEEK_API_KEY=sk-xxxx
DEFAULT_AI_PROVIDER=deepseek

# System configuration
SECRET_KEY=your-secret-key
```

### 3. Frontend Configuration

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Start Services

**Backend**:
```bash
cd backend
uvicorn run:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` to access the application.

## 📖 API Documentation

After starting the backend service, visit `http://localhost:8000/docs` to view the Swagger UI documentation.

### Main API Modules

| Module | Endpoint Prefix | Description |
|--------|-----------------|-------------|
| **Account Management** | `/api/accounts` | Login status check, QR code login, cookie login |
| **Article Management** | `/api/articles` | AI generation, manual creation, import/export, series generation |
| **Publishing Tasks** | `/api/publish` | Immediate publishing, scheduled publishing, bulk publishing |
| **Task Center** | `/api/tasks` | Task list, cancel tasks, calendar view |
| **Template Management** | `/api/templates` | AI prompt template management |
| **Data Analytics** | `/api/stats` | Dashboard statistics, optimal publishing time analysis |
| **Real-time Events** | `/api/events` | SSE event stream |

## ⚙️ Configuration Guide

In the **System Settings** page (`/settings`), you can configure:

- **AI Provider Selection**: Switch between different AI model providers.
- **Publishing Strategy**: Set publishing intervals and retry attempts on failure.
- **Browser Settings**: Enable/incognito mode, screenshot configurations.

## 📝 License

This project is intended solely for learning and research purposes. Please comply with Zhihu’s community guidelines and applicable laws and regulations, and do not abuse automated functions.