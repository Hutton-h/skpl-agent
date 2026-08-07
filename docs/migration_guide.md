# AgentScope to SKPL Agent Migration Guide

This guide helps you migrate from a standalone AgentScope deployment to
SKPL Agent, which extends AgentScope with context management, desktop
automation, web scraping, and more.

## Migration Overview

### What Changes

| Aspect | AgentScope | SKPL Agent |
|--------|-----------|------------|
| Package name | `agentscope` | `skpl_agent` |
| Import path | `import agentscope` | `import skpl_agent` |
| CLI command | `agentscope` | `skpl-agent` |
| Config prefix | `AGENTSCOPE_*` | `SKPL_CORE_*` |
| API routes | `/api/...` | `/api/...` (same) |
| Agent API | `Agent(...)` | `Agent(...)` (compatible) |

### What Stays the Same

- Agent runtime API is fully backward compatible
- Model abstraction (OpenAI, Anthropic, etc.) is unchanged
- Middleware pipeline is the same
- Storage backends are the same
- Workspace backends are the same
- Message bus is the same

### What's New

- Context management (OpenWolf integration)
- Desktop automation (Agent-S integration)
- Web scraping (Firecrawl integration)
- Code generation service
- Web intelligence service
- Token saving analysis
- Upstream update tracking
- Multi-tenant quota system

## Step-by-Step Migration

### Step 1: Update Dependencies

```bash
# Uninstall agentscope (optional, SKPL includes it)
pip uninstall agentscope

# Install SKPL Agent
pip install skpl-agent[service,context,web]
```

### Step 2: Update Imports

**AgentScope:**
```python
from agentscope.agent import Agent
from agentscope.model import OpenAIChatModel
from agentscope.middleware import TracingMiddleware
from agentscope.message import Msg
```

**SKPL Agent (direct replacement):**
```python
from skpl_agent.agent import Agent
from skpl_agent.model import OpenAIChatModel
from skpl_agent.middleware import TracingMiddleware
from skpl_agent.message import Msg
```

### Step 3: Update Configuration

**AgentScope (.env):**
```env
AGENTSCOPE_HOST=0.0.0.0
AGENTSCOPE_PORT=8000
AGENTSCOPE_DATABASE_URL=sqlite+aiosqlite:///data/agentscope.db
```

**SKPL Agent (.env):**
```env
SKPL_CORE_HOST=0.0.0.0
SKPL_CORE_PORT=8000
SKPL_CORE_DATABASE_URL=sqlite+aiosqlite:///data/skpl.db
```

### Step 4: Update CLI Commands

**AgentScope:**
```bash
agentscope serve
agentscope migrate
```

**SKPL Agent:**
```bash
skpl-agent serve
skpl-agent migrate
```

### Step 5: Migrate Database

SKPL Agent uses the same database schema for core tables. If you were using
AgentScope's SQL storage, you can migrate:

```bash
# Export from AgentScope
agentscope export --format json --output agentscope_backup.json

# Import to SKPL
skpl-agent import --format json --input agentscope_backup.json
```

Or use the migration script:

```bash
python backend/scripts/migrate_data.py \
  --source agentscope \
  --target skpl \
  --db-url sqlite+aiosqlite:///data/agentscope.db
```

### Step 6: Update Docker Configuration

**AgentScope docker-compose:**
```yaml
services:
  backend:
    image: agentscope/agentscope:latest
```

**SKPL Agent docker-compose:**
```yaml
services:
  backend:
    image: ghcr.io/skpl-agent/skpl-agent/backend:latest
  frontend:
    image: ghcr.io/skpl-agent/skpl-agent/frontend:latest
```

## API Compatibility

### Agent Configuration

AgentScope agent configuration is fully compatible:

```python
# AgentScope
agent = Agent(
    name="My Agent",
    model=OpenAIChatModel(model_name="gpt-4"),
    system_prompt="You are a helpful assistant.",
    middlewares=[TracingMiddleware()],
)

# SKPL Agent — identical API
agent = Agent(
    name="My Agent",
    model=OpenAIChatModel(model_name="gpt-4"),
    system_prompt="You are a helpful assistant.",
    middlewares=[TracingMiddleware()],
)
```

### Middleware

All AgentScope middleware classes work unchanged:

```python
from skpl_agent.middleware import (
    TracingMiddleware,
    RAGMiddleware,
    AgenticMemoryMiddleware,
    Mem0Middleware,
    TTSMiddleware,
)
```

### Storage

All storage backends are compatible:

```python
# SQL storage
from skpl_agent.storage import SqlStorage

# Redis storage
from skpl_agent.storage import RedisStorage

# S3 storage
from skpl_agent.storage import S3Storage
```

### Workspace

All workspace backends are compatible:

```python
from skpl_agent.workspace import (
    DockerWorkspace,
    K8sWorkspace,
    E2BWorkspace,
)
```

## New SKPL Features

Once migrated, you can use SKPL-specific features:

### Context Management

```python
from skpl_agent.context import AnatomyScanner, SessionContextManager

# Scan a codebase
scanner = AnatomyScanner(root_path="/path/to/project")
result = await scanner.scan()

# Create a session context
ctx = SessionContextManager(session_id="sess-1")
await ctx.initialize()
context = ctx.generate_context()
```

### Desktop Automation

```python
from skpl_agent.app._service import DesktopAutomationService

service = DesktopAutomationService()
result = await service.execute_action(
    node_id="node-001",
    action_type="click",
    parameters={"x": 100, "y": 200},
)
```

### Web Scraping

```python
from skpl_agent.app._service import FirecrawlService

service = FirecrawlService()
result = await service.scrape(
    url="https://example.com",
    formats=["markdown", "html"],
)
```

### Token Saving Analysis

```python
from skpl_agent.app._service import TokenSavingService

service = TokenSavingService()
result = service.compare(
    session_id="sess-1",
    query="fix the bug",
    context_text="Compact context from SKPL...",
    raw_content="Entire file content...",
)
print(f"Saved {result['saving_rate_pct']} tokens")
```

## Breaking Changes

### Environment Variables

All AgentScope `AGENTSCOPE_*` environment variables are now namespaced under
`SKPL_CORE_*`. However, the old variables are still read as fallback for
backward compatibility.

### CLI Entry Point

The CLI entry point is now `skpl-agent` instead of `agentscope`. The old
command is not available.

### Package Name

The package is now `skpl_agent` instead of `agentscope`. The old package name
is not available as a standalone package.

### Extra Dependencies

Extra dependency groups have been renamed:

| AgentScope | SKPL Agent |
|-----------|------------|
| `agentscope[gemini]` | `skpl-agent[model-gemini]` |
| `agentscope[ollama]` | `skpl-agent[model-ollama]` |
| `agentscope[service]` | `skpl-agent[service]` (same) |
| `agentscope[storage-redis]` | `skpl-agent[storage-redis]` (same) |
| `agentscope[workspace-docker]` | `skpl-agent[workspace-docker]` (same) |

## Rollback

If you need to roll back to AgentScope:

```bash
# Uninstall SKPL
pip uninstall skpl-agent

# Reinstall AgentScope
pip install agentscope[service,storage-sql]

# Restore database from backup
agentscope import --format json --input agentscope_backup.json

# Restore old configuration
# Rename SKPL_CORE_* env vars back to AGENTSCOPE_*
```

## FAQ

**Q: Can I run SKPL alongside AgentScope?**

A: Yes, as long as they use different ports and database files. The packages
are independent.

**Q: Will my custom AgentScope middleware work?**

A: Yes, if it extends `MiddlewareBase` from AgentScope. The middleware
interface is fully compatible.

**Q: Do I need to retrain my models?**

A: No. SKPL uses the same model abstraction as AgentScope.

**Q: What about custom tools?**

A: Custom tools registered via AgentScope's tool registration system will
work in SKPL.

**Q: Is the migration reversible?**

A: Yes. Export your data before migration and you can roll back at any time.