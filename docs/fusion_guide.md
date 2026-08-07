# SKPL Agent Fusion Guide

## How the Four Upstream Projects Are Integrated

SKPL Agent (Super Knowledge & Process Learning) is a unified agent platform that
fuses capabilities from four upstream open-source projects:

| Upstream | Primary Role | Technology Transferred |
|----------|-------------|----------------------|
| **AgentScope** | Multi-agent orchestration | Agent framework, model abstraction, middleware system, storage, workspace |
| **OpenWolf** | Context management | Codebase anatomy scanning, token budgeting, bug log, memory |
| **Agent-S** | Desktop automation | Desktop action execution, WebSocket communication, screenshot/OCR |
| **Firecrawl** | Web scraping | Web crawling, content extraction, SSRF protection |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        SKPL Agent Platform                       │
├───────────────┬───────────────┬──────────────┬──────────────────┤
│  AgentScope   │   OpenWolf    │   Agent-S    │    Firecrawl     │
│  (Core)       │  (Context)    │  (Desktop)   │    (Web)         │
├───────────────┼───────────────┼──────────────┼──────────────────┤
│ Agent runtime │ Anatomy scan  │ Desktop node │ Web crawler      │
│ Model API     │ Symbol store  │ WebSocket    │ Content extract  │
│ Middleware    │ Token ledger  │ Screenshot   │ SSRF protection  │
│ Storage       │ Bug log       │ OCR          │ Markdown output  │
│ Workspace     │ Cerebrum      │ Grounding    │ Rate limiting    │
│ Message bus   │ File watcher  │ Node mgmt    │ URL validation   │
└───────────────┴───────────────┴──────────────┴──────────────────┘
```

---

## 1. AgentScope (Core Agent Framework)

### What We Use

AgentScope provides the foundational multi-agent framework. SKPL Agent is built
directly on top of AgentScope's agent runtime, middleware pipeline, and service
layer.

**Key modules inherited:**

- `agent/` — Agent base class, configuration, structured output tools
- `model/` — Multi-provider LLM abstraction (OpenAI, Anthropic, DashScope, etc.)
- `middleware/` — Extensible middleware pipeline (tracing, RAG, memory, TTS)
- `app/` — FastAPI service layer, routers, storage, workspaces
- `message_bus/` — In-memory and Redis-backed message bus for agent communication
- `workspace/` — Sandboxed code execution environments (Docker, K8s, E2B)
- `storage/` — SQL, Redis, S3 storage backends for sessions and data

### How We Extend

SKPL adds:

- **SKPL-specific routers** in `app/_router/`:
  - `context_router.py` — Context management API
  - `desktop_automation_router.py` — Desktop automation API
  - `firecrawl_router.py` — Web scraping API
  - `web_intelligence_router.py` — Web intelligence API
  - `code_generation_router.py` — Code generation API
  - `quota_router.py` — Quota management API

- **SKPL-specific services** in `app/_service/`:
  - `context_service.py` — Context orchestration
  - `desktop_automation_service.py` — Desktop automation
  - `firecrawl_service.py` — Web scraping
  - `web_intelligence_service.py` — Web intelligence
  - `code_generation_service.py` — Code generation
  - `token_ledger_service.py` — Token budgeting
  - `token_saving_service.py` — Token saving A/B comparison
  - `quota_service.py` — Multi-tenant quotas
  - `rate_limit_service.py` — Rate limiting

- **SKPL-specific managers** in `app/_manager/`:
  - `_context_manager.py` — Session context lifecycle
  - `_file_watch_manager.py` — File change detection
  - `_scan_task_manager.py` — Anatomy scan orchestration
  - `_update_manager.py` — Upstream update checking (APScheduler)

- **SKPL-specific middleware** in `app/_middleware/`:
  - `context_middleware.py` — Context injection middleware
  - `token_middleware.py` — Token budget middleware
  - `quota_middleware.py` — Quota enforcement middleware
  - `grounding_middleware.py` — UI grounding middleware

### Import Strategy

All AgentScope imports go through the `skpl_agent` namespace. The `pyproject.toml`
declares AgentScope dependencies as part of the core dependencies. SKPL's
`__init__.py` re-exports AgentScope's public API alongside SKPL additions.

---

## 2. OpenWolf (Context Management)

### What We Use

OpenWolf's context management system provides intelligent codebase understanding
through:

- **Anatomy Scanner** — Tree-sitter-based code analysis that extracts symbols,
  definitions, references, and structure from source code
- **Anatomy Store** — Dual-mode storage (SQLite + JSON) for symbol data
- **Token Ledger** — Token usage tracking and budget enforcement
- **Bug Log** — Bug deduplication using Jaccard similarity
- **Cerebrum** — Session memory and context aggregation
- **Waste Detector** — Identifies wasteful token usage patterns
- **Sensitive Filter** — Detects and redacts sensitive content from context
- **File Watcher** — Real-time file change detection for incremental updates

### How We Integrate

The OpenWolf modules are integrated directly into the SKPL package structure:

```
skpl_agent/
├── context/
│   ├── anatomy_scanner.py    # Tree-sitter code scanning
│   ├── anatomy_store.py      # SQLite/JSON symbol storage
│   ├── token_ledger.py       # Token usage & budget
│   ├── token_estimator.py    # tiktoken-based estimation
│   ├── token_estimator_claude.py  # Claude-specific estimation
│   ├── buglog.py             # Bug deduplication
│   ├── cerebrum.py           # Memory & reasoning
│   ├── waste_detector.py     # Waste pattern detection
│   ├── sensitive_filter.py   # Sensitive content filtering
│   ├── session_context.py    # Session context manager
│   ├── symbol_extractor.py   # Symbol extraction helpers
│   └── bug_matcher.py        # Bug similarity matching
```

The `ContextManager` in `app/_manager/_context_manager.py` ties these
together into the FastAPI application lifecycle.

### Data Flow

```
Codebase → AnatomyScanner → AnatomyStore → ContextManager → LLM Context
                ↑                                    ↑
          FileWatchManager                    TokenLedger
                ↑                                    ↑
          ScanTaskManager                     WasteDetector
```

---

## 3. Agent-S (Desktop Automation)

### What We Use

Agent-S provides desktop automation capabilities through a client-server
architecture:

- **Desktop Node** — Runs on the user's machine, executes desktop actions
- **WebSocket Communication** — Real-time bidirectional communication
- **Action Types** — Click, type, scroll, screenshot, OCR, drag, hotkey
- **Node Registry** — Tracks connected desktop nodes and their status
- **Rate Limiting** — Token bucket algorithm for per-node action limits
- **Scheduling** — Time-based desktop action scheduling

### How We Integrate

The desktop automation system is split into two parts:

**Server side (control center):**
```
skpl_agent/app/_service/
├── desktop_automation_service.py   # Action orchestration
├── desktop_service.py              # Node management
├── desktop_scheduler.py            # Scheduled actions
├── node_registry.py                # Node tracking
└── rate_limit_service.py           # Rate limiting
```

**Client side (desktop node):**
```
skpl_agent/desktop_node/
├── cli.py           # Desktop node CLI entry point
├── server.py        # WebSocket server
├── actions.py       # Desktop action implementations
└── auth.py          # JWT authentication
```

**API layer:**
```
skpl_agent/app/_router/
├── desktop_automation_router.py    # REST API for desktop actions
└── _schema/_desktop_automation.py  # Pydantic schemas
```

### Communication Protocol

```
Desktop Node (Windows) ←──WebSocket (TLS + JWT)──→ Control Center (Linux)
        │                                                  │
        ├── Heartbeat (every 30s)                          │
        ├── Execute action (click, type, etc.)             │
        ├── Screenshot (base64 JPEG)                       │
        └── OCR result (text)                              │
                                                           │
                                              REST API ──→ Frontend
```

---

## 4. Firecrawl (Web Scraping)

### What We Use

Firecrawl provides production-grade web scraping and crawling:

- **Multi-engine scraping** — Crawl4AI, BeautifulSoup, lxml, Trafilatura
- **Content extraction** — Markdown, HTML, plain text output formats
- **SSRF protection** — DNS rebinding protection, private network blocking
- **Rate limiting** — Per-domain delay and concurrency control
- **Content validation** — Size limits, format validation, encoding detection

### How We Integrate

```
skpl_agent/app/_service/
├── firecrawl_service.py            # Web scraping orchestration
└── web_intelligence_service.py     # Intelligent web research

skpl_agent/app/_router/
├── firecrawl_router.py             # REST API for scraping
└── web_intelligence_router.py      # REST API for web research

skpl_agent/app/_security/
└── ssrf.py                         # SSRF protection middleware
```

### Scraping Pipeline

```
URL → SSRF Check → DNS Resolve → HTTP Request → Content Extract → Format → Return
         │              │              │              │               │
    Block private    Prevent       Rate limit     Parse HTML     Markdown
    networks         rebinding     per domain     /JSON/text     HTML, Text
```

---

## 5. Cross-Cutting Concerns

### Configuration

All four subsystems are configured through a unified Pydantic Settings model
in `config.py`:

```python
class Settings(BaseSettings):
    core: CoreSettings        # AgentScope server settings
    context: ContextSettings  # OpenWolf context settings
    desktop: DesktopSettings  # Agent-S desktop settings
    web: WebSettings          # Firecrawl web settings
    update: UpdateSettings    # Upstream update settings
    quota: QuotaSettings      # Multi-tenant quota settings
```

Environment variables use namespaced prefixes:
- `SKPL_CORE_*` for core settings
- `SKPL_CONTEXT_*` for context settings
- `SKPL_DESKTOP_*` for desktop settings
- `SKPL_WEB_*` for web settings
- `SKPL_UPDATE_*` for update settings
- `SKPL_QUOTA_*` for quota settings

### Tracing

The OpenTelemetry tracing middleware from AgentScope is extended with
SKPL-specific spans in `middleware/_tracing/_skpl_spans.py`:

- `context_scan_span()` — Context anatomy scan tracing
- `desktop_action_span()` — Desktop action tracing
- `firecrawl_request_span()` — Web scraping request tracing
- `code_generation_span()` — Code generation tracing

### Upstream Update Tracking

The `updates/` module monitors all four upstream repositories for new commits
and releases:

- `updates/__init__.py` — UpdateChecker and data classes
- `updates/service.py` — UpdateService with lifecycle management
- `updates/merger.py` — Safe merge of upstream changes
- `updates/sources.json` — Repository configuration
- `.github/workflows/update-check.yml` — Scheduled CI check

---

## 6. Directory Map

```
skpl-agent/
├── backend/src/skpl_agent/
│   ├── agent/              # AgentScope: agent runtime
│   ├── model/              # AgentScope: LLM abstraction
│   ├── middleware/         # AgentScope: middleware pipeline
│   │   └── _tracing/       # AgentScope: OpenTelemetry tracing
│   │       └── _skpl_spans.py  # SKPL: custom spans
│   ├── app/                # AgentScope + SKPL: FastAPI application
│   │   ├── _manager/       # SKPL: lifecycle managers
│   │   ├── _service/       # SKPL: business logic services
│   │   ├── _router/        # SKPL: API routes
│   │   ├── _middleware/    # SKPL: app-level middleware
│   │   └── _security/      # SKPL: security (SSRF)
│   ├── context/            # OpenWolf: context management
│   ├── desktop_node/       # Agent-S: desktop node client
│   ├── updates/            # SKPL: upstream update tracking
│   ├── workspace/          # AgentScope: sandbox environments
│   ├── storage/            # AgentScope: data persistence
│   ├── message_bus/        # AgentScope: inter-agent messaging
│   └── config.py           # SKPL: unified configuration
├── frontend/               # React + TypeScript frontend
├── deploy/                 # Kubernetes, database, nginx configs
├── docs/                   # Documentation
└── .github/                # CI/CD workflows
```

---

## 7. Dependency Graph

```
SKPL Agent
├── AgentScope (core)
│   ├── FastAPI + Uvicorn
│   ├── SQLAlchemy + Alembic
│   ├── OpenTelemetry
│   ├── APScheduler
│   └── Multiple LLM SDKs
├── OpenWolf (context)
│   ├── Tree-sitter (multi-language)
│   ├── SQLite (aiosqlite)
│   ├── tiktoken
│   └── regex
├── Agent-S (desktop)
│   ├── WebSocket (websockets)
│   ├── PyAutoGUI
│   ├── Pillow + MSS
│   ├── PyJWT
│   └── Optional: PaddleOCR, PyTorch
└── Firecrawl (web)
    ├── Crawl4AI
    ├── BeautifulSoup4 + lxml
    ├── Trafilatura
    └── markdownify
```

---

## 8. Contribution Guidelines

When contributing to SKPL Agent, follow these rules:

1. **Upstream Compatibility**: Changes to AgentScope-derived modules should
   maintain backward compatibility with the upstream API.

2. **Import Convention**: Use `from skpl_agent.xxx import yyy` for all
   internal imports. Do not import directly from upstream packages.

3. **Configuration**: All new settings go through the unified `Settings` model.

4. **Testing**: Add tests for new functionality. Use the existing test
   structure: `unit/`, `integration/`, `parity/`, `performance/`.

5. **Upstream Updates**: When upstream repos release new versions, run the
   update check workflow and review breaking changes before merging.