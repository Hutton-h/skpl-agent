# SKPL Agent — 5-Minute Quick Start

Get SKPL Agent running on your machine in 5 minutes.

## Prerequisites

- **Python** 3.11 or later
- **Node.js** 22 or later
- **pnpm** 11.17 or later (`npm install -g pnpm`)
- **Git** (for cloning)

## Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/skpl-agent/skpl-agent.git
cd skpl-agent

# Install backend dependencies
pip install -e ".[service,context]"

# Install frontend dependencies
cd frontend
pnpm install
cd ..
```

## Step 2: Start the Backend

```bash
# Start the SKPL agent server (default: http://localhost:8000)
python -m skpl_agent serve
```

The server starts with:
- REST API at `http://localhost:8000`
- WebSocket endpoint at `http://localhost:8000/ws`
- API docs at `http://localhost:8000/docs`

## Step 3: Start the Frontend

Open a **new terminal**:

```bash
cd frontend
pnpm dev
```

The frontend starts at `http://localhost:5173` and proxies API requests to
the backend.

## Step 4: Complete Setup

1. Open `http://localhost:5173` in your browser
2. You will see the setup page — enter your backend URL (`http://localhost:8000`)
3. Configure your LLM provider (API key, model name)
4. Click "Complete Setup"

## Step 5: Try It Out

1. Go to **Dashboard** to see the overview
2. Go to **Chat** to start a conversation with an agent
3. Go to **Context** to scan a codebase for context management
4. Go to **Firecrawl** to scrape a web page
5. Go to **Desktop** to manage desktop automation nodes

## What's Included

- **Multi-agent chat** — AI agents with tool calling, middleware, and memory
- **Codebase context** — Tree-sitter-powered code understanding and token budgeting
- **Web scraping** — SSRF-safe web content extraction
- **Desktop automation** — Remote desktop control via WebSocket
- **Code generation** — AI-assisted code generation with diff preview
- **Web intelligence** — Intelligent web research and summarization

## Next Steps

- Read the [Architecture Guide](architecture.md) for system design
- Read the [Configuration Guide](configuration.md) for all settings
- Read the [Fusion Guide](fusion_guide.md) for upstream integration details
- Read the [Module Map](module_map.md) for code organization
- Read the [Development Guide](development.md) for contributing

## Troubleshooting

**Backend won't start:**
```bash
# Check Python version
python --version  # Must be >= 3.11

# Reinstall dependencies
pip install -e ".[service,context]"
```

**Frontend won't start:**
```bash
# Check Node.js version
node --version  # Must be >= 22

# Clear cache and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

**API calls fail:**
- Make sure the backend is running on port 8000
- Check the Vite proxy config in `frontend/vite.config.ts`
- Verify the backend URL in `localStorage.getItem('server_url')`

**Desktop node not connecting:**
- The desktop node requires Windows and desktop dependencies
- Install with: `pip install -e ".[desktop]"`
- Start with: `python -m skpl_agent.desktop_node serve`