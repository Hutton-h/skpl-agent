# SKPL Agent — Unified Concept Model

## Core Concepts

### 1. Agent

An autonomous or semi-autonomous entity that can perceive its environment,
reason about goals, and take actions through tools.

**Properties:**
- `agent_id`: Unique identifier
- `name`: Human-readable name
- `model`: LLM configuration (provider, model name, parameters)
- `system_prompt`: Base instructions for the agent
- `middlewares`: Ordered list of middleware modules
- `tools`: Available tools and skills
- `memory`: Long-term memory configuration

**Lifecycle:**
```
Create → Configure → Deploy → Chat → Terminate
```

**Relationships:**
- An Agent belongs to one **Tenant**
- An Agent participates in multiple **Sessions**
- An Agent uses one **Model** at a time
- An Agent has a **Context** for each session

---

### 2. Session

A conversation context between a user and one or more agents.

**Properties:**
- `session_id`: Unique identifier
- `agent_id`: The primary agent
- `status`: active, paused, completed
- `messages`: Ordered list of chat messages
- `context`: Session-specific context data
- `token_budget`: Maximum token usage for this session

**Lifecycle:**
```
Create → Active → Paused → Resumed → Completed
```

**Relationships:**
- A Session belongs to one **Agent**
- A Session contains multiple **Messages**
- A Session has one **SessionContext**
- A Session has one **TokenLedger**

---

### 3. Message

A single turn in a conversation.

**Properties:**
- `message_id`: Unique identifier
- `role`: user, assistant, system, tool
- `content`: Text content
- `tool_calls`: Optional tool invocations
- `tool_results`: Optional tool execution results
- `timestamp`: When the message was created

**Relationships:**
- A Message belongs to one **Session**
- A Message may trigger **Tool** executions
- A Message is tracked by the **TokenLedger**

---

### 4. Context (Codebase Understanding)

The system's understanding of a codebase, used to provide relevant
information to the LLM without exceeding token limits.

**Sub-concepts:**

#### 4a. Anatomy

The structural analysis of source code, extracted via Tree-sitter.

**Properties:**
- `symbols`: Functions, classes, variables, imports
- `definitions`: Where symbols are defined
- `references`: Where symbols are used
- `structure`: File and directory hierarchy

**Storage:** Dual-mode (SQLite + JSON) via **AnatomyStore**

#### 4b. Token Ledger

Tracks token usage across a session for budget enforcement.

**Properties:**
- `entries`: List of token usage records
- `total_tokens`: Cumulative token count
- `budget`: Maximum allowed tokens
- `waste_tokens`: Tokens identified as wasteful

**Operations:** record, check_budget, estimate_cost, detect_waste

#### 4c. Bug Log

Records and deduplicates bugs encountered during development.

**Properties:**
- `records`: Bug entries with error type, message, traceback
- `jaccard_threshold`: Similarity threshold for deduplication

**Operations:** log, match, get_recent, get_statistics

#### 4d. Cerebrum (Memory)

Session-scoped key-value memory with confidence scoring.

**Properties:**
- `memories`: Key-value pairs with category and confidence
- `capacity`: Maximum number of memories

**Operations:** remember, recall, forget, summarize

---

### 5. Desktop Automation

Remote control of a desktop machine through WebSocket communication.

**Concepts:**

#### 5a. Desktop Node

A machine running the desktop automation agent.

**Properties:**
- `node_id`: Unique identifier
- `hostname`: Machine hostname
- `status`: online, offline, connecting
- `os`: Operating system (Windows, macOS, Linux)
- `version`: Node software version
- `capabilities`: Available actions (click, type, screenshot, OCR)

**Lifecycle:**
```
Register → Connect → Heartbeat → Disconnect → Cleanup
```

#### 5b. Desktop Action

A single operation executed on a desktop node.

**Types:** click, type, scroll, screenshot, OCR, drag, hotkey, wait

**Properties:**
- `action_type`: Type of action
- `target`: Coordinates, element selector, or text
- `parameters`: Action-specific parameters
- `timeout`: Maximum execution time
- `result`: Action output (screenshot base64, OCR text, etc.)

---

### 6. Web Scraping

Extracting and processing content from web pages.

**Concepts:**

#### 6a. Crawl Request

A request to fetch and process a web page.

**Properties:**
- `url`: Target URL
- `mode`: scrape (single page), crawl (follow links), map (URL discovery)
- `formats`: Output formats (markdown, html, text)
- `max_depth`: For crawl mode, how deep to follow links
- `filters`: URL inclusion/exclusion patterns

#### 6b. SSRF Protection

Security layer preventing Server-Side Request Forgery.

**Properties:**
- `blocked_networks`: Private IP ranges to block
- `allowed_domains`: Explicit whitelist
- `dns_rebinding_protection`: Prevent DNS rebinding attacks
- `block_localhost`: Block localhost access

---

### 7. Tenant & Quota

Multi-tenant resource isolation and limits.

**Concepts:**

#### 7a. Tenant

An isolated organization or user group.

**Properties:**
- `tenant_id`: Unique identifier
- `name`: Organization name
- `quota_limits`: Resource limits for this tenant

#### 7b. Quota

Resource usage limits per tenant.

**Properties:**
- `max_agents`: Maximum agent count
- `max_sessions`: Maximum concurrent sessions
- `max_workspaces`: Maximum workspace count
- `max_desktop_nodes`: Maximum desktop nodes
- `max_web_requests_per_day`: Daily web request limit
- `max_token_budget`: Total token budget
- `max_storage_mb`: Storage limit in megabytes

**Operations:** check, reserve, release, report

---

### 8. Upstream Update

Tracking changes in the four upstream repositories.

**Concepts:**

#### 8a. Upstream Repository

A source project that SKPL Agent integrates with.

**Properties:**
- `name`: Repository name (agentscope, openwolf, agent-s, firecrawl)
- `url`: GitHub URL
- `branch`: Tracked branch
- `enabled`: Whether tracking is active

#### 8b. Update Check

A periodic comparison of local vs upstream state.

**Properties:**
- `checked_at`: Timestamp of check
- `has_updates`: Whether new commits exist
- `commits_behind`: Number of commits behind upstream
- `latest_tag`: Most recent upstream tag
- `breaking_changes`: Detected breaking changes

---

## Concept Relationships

```
Tenant 1──* Agent
Agent  1──* Session
Agent  1──* Middleware
Agent  1──1 Model
Session 1──* Message
Session 1──1 SessionContext
Session 1──1 TokenLedger
SessionContext 1──1 AnatomyStore
SessionContext 1──1 BugLog
SessionContext 1──1 Cerebrum
Tenant 1──* DesktopNode
DesktopNode 1──* DesktopAction
Tenant 1──* CrawlRequest
CrawlRequest 1──1 SSRFCheck
Tenant 1──1 Quota
UpstreamRepo 1──* UpdateCheck
```

### Legend

- `1──1` : One-to-one relationship
- `1──*` : One-to-many relationship
- `*──*` : Many-to-many relationship

---

## State Machine: Session Lifecycle

```
  ┌─────────┐     create     ┌──────────┐    complete    ┌───────────┐
  │  None   │ ─────────────→ │  Active  │ ──────────────→ │ Completed │
  └─────────┘                └──────────┘                 └───────────┘
                                  │  ▲
                                  │  │ resume
                                  ▼  │
                             ┌──────────┐
                             │  Paused  │
                             └──────────┘
```

## State Machine: Desktop Node

```
  ┌──────────┐   connect    ┌──────────┐   disconnect   ┌───────────┐
  │ Offline  │ ────────────→│  Online  │ ──────────────→ │  Offline  │
  └──────────┘              └──────────┘                 └───────────┘
       ▲                         │
       │      heartbeat lost     │  heartbeat received
       └─────────────────────────┘
```