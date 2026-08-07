# SKPL Agent Module Map

## Package Structure

```
skpl_agent/                          # Root package
├── __init__.py                      # Package entry, re-exports public API
├── __main__.py                      # `python -m skpl_agent` entry point
├── _logging.py                      # Structured logging setup (structlog)
├── _version.py                      # Version string (__version__)
├── cli.py                           # CLI entry point (click)
├── config.py                        # Unified Pydantic Settings configuration
├── py.typed                         # PEP 561 marker
│
├── _utils/                          # Utility functions
│   ├── __init__.py
│   ├── _audio.py                    # Audio processing utilities
│   ├── _common.py                   # Common helper functions
│   └── _mixin.py                    # Mixin classes
│
├── agent/                           # Agent runtime (from AgentScope)
│   ├── __init__.py
│   ├── _agent.py                    # Base Agent class
│   ├── _config.py                   # Agent configuration
│   ├── _structured_output_tool.py   # Structured output parsing
│   └── _utils.py                    # Agent utility functions
│
├── model/                           # LLM abstraction (from AgentScope)
│   ├── __init__.py
│   ├── _model.py                    # ChatModelBase
│   ├── _openai.py                   # OpenAI-compatible models
│   ├── _anthropic.py                # Anthropic Claude models
│   ├── _dashscope.py                # Alibaba DashScope models
│   └── _gemini.py                   # Google Gemini models
│
├── middleware/                       # Agent middleware pipeline
│   ├── __init__.py                  # Public API exports
│   ├── _base.py                     # MiddlewareBase abstract class
│   ├── _rag.py                      # RAG middleware
│   ├── _budget.py                   # Reply budget control
│   ├── _longterm_memory.py          # Long-term memory middleware
│   ├── _tts_middleware.py           # Text-to-speech middleware
│   ├── context_middleware.py        # SKPL: Context injection
│   ├── token_middleware.py          # SKPL: Token budget enforcement
│   └── _tracing/                    # OpenTelemetry tracing
│       ├── __init__.py
│       ├── _trace.py                # TracingMiddleware
│       ├── _attributes.py           # Span attribute constants
│       ├── _converter.py            # Value conversion
│       ├── _extractor.py            # Attribute extraction
│       ├── _setup.py               # Tracer provider setup
│       ├── _utils.py               # Tracing utilities
│       └── _skpl_spans.py          # SKPL-specific span definitions
│
├── app/                             # FastAPI application (service layer)
│   ├── __init__.py
│   ├── _app.py                      # FastAPI app factory
│   ├── _bus_ops.py                  # Message bus operations
│   ├── _lifespan.py                 # Application lifecycle (startup/shutdown)
│   ├── _types.py                    # Application type definitions
│   ├── deps.py                      # FastAPI dependency injection
│   ├── desktop_agent.py             # Desktop agent integration
│   │
│   ├── _manager/                    # Lifecycle managers
│   │   ├── __init__.py
│   │   ├── _background_task_manager.py  # Background task execution
│   │   ├── _cancel_dispatcher.py        # Agent cancellation
│   │   ├── _chat_run_registry.py        # Chat run tracking
│   │   ├── _context_manager.py          # Context session lifecycle
│   │   ├── _file_watch_manager.py       # File change detection
│   │   ├── _scan_task_manager.py        # Anatomy scan orchestration
│   │   ├── _scheduler/                  # Job scheduling
│   │   │   ├── __init__.py
│   │   │   └── _scheduler_manager.py    # Schedule CRUD and execution
│   │   ├── _update_manager.py           # Upstream update checking (APScheduler)
│   │   └── _wakeup_dispatcher.py        # Scheduled wake-up
│   │
│   ├── _service/                    # Business logic services
│   │   ├── __init__.py
│   │   ├── _access.py               # Resource access control
│   │   ├── _chat.py                 # Chat execution service
│   │   ├── _embedding.py            # Embedding model management
│   │   ├── _index_sweeper.py        # Index cleanup
│   │   ├── _index_task_consumer.py  # Index task consumption
│   │   ├── _index_worker.py         # Index building worker
│   │   ├── _knowledge_base.py       # Knowledge base management
│   │   ├── _model.py               # Model management
│   │   ├── _session.py             # Session management
│   │   ├── _session_projection.py  # Session projection
│   │   ├── _toolkit.py             # Tool management
│   │   ├── _tts_model.py           # TTS model management
│   │   ├── _projectors/            # Projection strategies
│   │   │   ├── __init__.py
│   │   │   └── _subagent_hitl.py  # Subagent human-in-the-loop
│   │   ├── anatomy_service.py      # SKPL: Anatomy scan service
│   │   ├── buglog_service.py       # SKPL: Bug log service
│   │   ├── cerebrum_service.py     # SKPL: Memory service
│   │   ├── context_service.py      # SKPL: Context orchestration
│   │   ├── code_generation_service.py  # SKPL: Code generation
│   │   ├── desktop_automation_service.py # SKPL: Desktop actions
│   │   ├── desktop_service.py      # SKPL: Desktop node management
│   │   ├── desktop_scheduler.py    # SKPL: Desktop action scheduling
│   │   ├── firecrawl_service.py    # SKPL: Web scraping
│   │   ├── node_registry.py        # SKPL: Desktop node registry
│   │   ├── quota_service.py        # SKPL: Multi-tenant quotas
│   │   ├── rate_limit_service.py   # SKPL: Rate limiting
│   │   ├── token_ledger_service.py # SKPL: Token budgeting
│   │   ├── token_saving_service.py # SKPL: Token saving A/B comparison
│   │   └── web_intelligence_service.py # SKPL: Web research
│   │
│   ├── _router/                    # HTTP API routes
│   │   ├── __init__.py
│   │   ├── _agent.py               # Agent management
│   │   ├── _chat.py               # Chat endpoints
│   │   ├── _credential.py          # Credential management
│   │   ├── _knowledge_base.py      # Knowledge base management
│   │   ├── _model.py              # Model management
│   │   ├── _schedule.py           # Schedule management
│   │   ├── _session.py            # Session management
│   │   ├── _tts_model.py           # TTS model management
│   │   ├── _workspace.py          # Workspace management
│   │   ├── context_router.py      # SKPL: Context API
│   │   ├── desktop_automation_router.py  # SKPL: Desktop API
│   │   ├── firecrawl_router.py    # SKPL: Web scraping API
│   │   ├── web_intelligence_router.py  # SKPL: Web intelligence API
│   │   ├── code_generation_router.py   # SKPL: Code generation API
│   │   ├── quota_router.py        # SKPL: Quota management API
│   │   └── _schema/               # Request/response schemas
│   │       ├── __init__.py
│   │       ├── _agent.py
│   │       ├── _chat.py
│   │       ├── _code_generation.py
│   │       ├── _common.py
│   │       ├── _context.py
│   │       ├── _credential.py
│   │       ├── _desktop_automation.py
│   │       ├── _knowledge_base.py
│   │       ├── _mcp.py
│   │       ├── _model.py
│   │       ├── _schedule.py
│   │       ├── _session.py
│   │       ├── _tts_model.py
│   │       └── _web_intelligence.py
│   │
│   ├── _middleware/                # App-level middleware
│   │   ├── grounding_middleware.py # SKPL: UI grounding
│   │   └── quota_middleware.py     # SKPL: Quota enforcement
│   │
│   ├── _security/                  # Security utilities
│   │   ├── __init__.py
│   │   └── ssrf.py                # SSRF protection
│   │
│   ├── _tool/                      # Agent tools
│   │   ├── __init__.py
│   │   ├── _agent_create.py
│   │   ├── _agent_invite.py
│   │   ├── _constants.py
│   │   ├── _team_create.py
│   │   ├── _team_delete.py
│   │   ├── _team_say.py
│   │   └── _team_tool_base.py
│   │
│   ├── _ws/                        # WebSocket handlers
│   │   ├── __init__.py
│   │   └── desktop_ws_handler.py  # SKPL: Desktop WebSocket
│   │
│   ├── access/                     # Access control
│   │   ├── __init__.py
│   │   └── _policy.py
│   │
│   ├── message_bus/                # Inter-agent messaging
│   │   ├── __init__.py
│   │   ├── _base.py
│   │   ├── _in_memory_message_bus.py
│   │   ├── _keys.py
│   │   └── _redis_message_bus.py
│   │
│   └── _event/                     # Event system
│       ├── __init__.py
│       └── _custom.py
│
├── context/                        # Context management (from OpenWolf)
│   ├── __init__.py
│   ├── anatomy_scanner.py          # Tree-sitter code scanning
│   ├── anatomy_store.py            # SQLite/JSON symbol storage
│   ├── token_ledger.py             # Token usage tracking
│   ├── token_estimator.py          # Token counting (tiktoken)
│   ├── token_estimator_claude.py   # Claude-specific estimation
│   ├── buglog.py                   # Bug deduplication
│   ├── cerebrum.py                 # Memory & reasoning
│   ├── waste_detector.py           # Waste pattern detection
│   ├── sensitive_filter.py         # Sensitive content filtering
│   ├── session_context.py          # Session context manager
│   ├── symbol_extractor.py         # Symbol extraction helpers
│   └── bug_matcher.py              # Bug similarity matching
│
├── desktop_node/                   # Desktop automation (from Agent-S)
│   ├── __init__.py
│   ├── cli.py                      # Node CLI entry point
│   ├── server.py                   # WebSocket server
│   ├── actions.py                  # Desktop action implementations
│   └── auth.py                     # JWT authentication
│
├── updates/                        # Upstream update tracking
│   ├── __init__.py                 # UpdateChecker, data classes
│   ├── service.py                  # UpdateService lifecycle
│   ├── merger.py                   # Safe merge engine
│   ├── router.py                   # Update API routes
│   └── sources.json                # Upstream repo configuration
│
├── workspace/                      # Sandboxed execution (from AgentScope)
│   ├── __init__.py
│   ├── _base.py
│   ├── _docker.py
│   ├── _e2b.py
│   ├── _k8s.py
│   └── _opensandbox.py
│
├── storage/                        # Data persistence (from AgentScope)
│   ├── __init__.py
│   ├── _base.py
│   ├── _sql/
│   ├── _redis.py
│   └── _s3.py
│
└── skill/                          # Agent skills
    ├── __init__.py
    └── _firecrawl.py              # Firecrawl web scraping skill
```

## Module Responsibility Summary

| Module | Responsibility | Source |
|--------|---------------|--------|
| `agent/` | Agent runtime, lifecycle, configuration | AgentScope |
| `model/` | LLM abstraction, multi-provider support | AgentScope |
| `middleware/` | Agent middleware pipeline | AgentScope + SKPL |
| `app/_manager/` | Application lifecycle managers | SKPL |
| `app/_service/` | Business logic services | AgentScope + SKPL |
| `app/_router/` | HTTP API endpoints | AgentScope + SKPL |
| `app/_security/` | Security utilities (SSRF) | SKPL |
| `context/` | Codebase context management | OpenWolf |
| `desktop_node/` | Desktop automation client | Agent-S |
| `updates/` | Upstream update tracking | SKPL |
| `workspace/` | Sandboxed code execution | AgentScope |
| `storage/` | Data persistence | AgentScope |
| `config.py` | Unified configuration | SKPL |
| `_logging.py` | Structured logging | AgentScope |
| `cli.py` | Command-line interface | SKPL |