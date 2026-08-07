# SKPL Agent 架构设计

## 概述

SKPL Agent 融合了四个上游项目的核心能力：AgentScope（多Agent框架）、OpenWolf（上下文管理）、Agent-S（桌面自动化）、Firecrawl（网页抓取）。采用五层架构设计，支持多租户、多Agent协作和桌面节点分布式部署。

## 五层架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend 展示层                        │
│  React 19 + TypeScript 6 + TailwindCSS 4 + shadcn/ui    │
├─────────────────────────────────────────────────────────┤
│                   Middleware 层                          │
│  上下文注入 | Token追踪 | 限流 | 配额 | SSRF防护 | 协议转换 │
├─────────────────────────────────────────────────────────┤
│                   核心 Agent 层                           │
│  Agent引擎 | 工具系统 | 模型适配 | 工作空间 | RAG | 记忆   │
├─────────────────────────────────────────────────────────┤
│                    服务层                                │
│  Chat | Session | Model | KnowledgeBase | Scheduler     │
│  Context | Anatomy | BugLog | Cerebrum | TokenLedger    │
│  Desktop Automation | Web Intelligence | Code Generation│
│  Firecrawl | Quota | RateLimit | Updates               │
├─────────────────────────────────────────────────────────┤
│                   基础设施层                              │
│  PostgreSQL | Redis | 消息总线 | 存储 | 事件系统 | CLI    │
└─────────────────────────────────────────────────────────┘
```

### 展示层

- **框架**: React 19 + TypeScript 6 + Vite 8
- **UI**: TailwindCSS 4 + shadcn/ui + Radix UI
- **路由**: React Router v7
- **国际化**: i18next (中/英)
- **动画**: Framer Motion
- **状态管理**: React Context + Hooks
- **图表**: Recharts + 自定义组件

### Middleware 层

中间件层负责请求处理管道，包括：

| 中间件 | 功能 | 来源 |
|--------|------|------|
| ContextMiddleware | 会话生命周期管理，注入项目上下文 | OpenWolf |
| TokenMiddleware | Token 用量追踪和预算控制 | OpenWolf |
| QuotaMiddleware | 多租户配额强制执行 | SKPL |
| RateLimitMiddleware | 令牌桶速率限制 | SKPL |
| SSRFProtection | 服务端请求伪造防护 | SKPL |
| GroundingMiddleware | 桌面截图 UI 元素检测 | Agent-S |
| ProtocolMiddleware | AGUI 协议转换 | AgentScope |

### 核心 Agent 层

**Agent 引擎** (AgentScope)：支持多种 Agent 类型（ReAct、Plan-and-Execute、自定义），提供工具调用、结构化输出和生命周期管理。

**模型适配层**：11 个模型后端，统一接口：
- OpenAI Chat / Response API
- Anthropic Claude (haiku/opus/sonnet)
- Google Gemini (2.5/3.x)
- 阿里 DashScope (qwen/deepseek/glm)
- DeepSeek (chat/reasoner/v4)
- Moonshot/Kimi (k2.5/k2.6/k3)
- Ollama 本地模型
- xAI Grok

**工具系统**：内置工具（bash、edit、glob、grep、read、write、powershell、skill）+ 扩展工具注册机制。

**工作空间**：7 种沙箱后端（Docker、E2B、Daytona、Kubernetes、Bubblewrap、OpenSandbox、本地），支持安全代码执行。

**RAG 系统**：4 种向量数据库（Qdrant、Milvus、MongoDB、Elasticsearch）+ 多种文档解析器（PDF、PPTX、DOCX、XLSX）。

**长期记忆**：Mem0、Reme、Agentic Memory 三种方案。

### 服务层

服务层实现业务逻辑，与路由层分离：

| 服务 | 功能 |
|------|------|
| ContextService | 上下文聚合和注入 |
| AnatomyService | 项目结构扫描和符号提取 |
| BugLogService | Bug 记录和去重 |
| CerebrumService | 上下文大脑调度 |
| TokenLedgerService | Token 用量统计 |
| DesktopAutomationService | 桌面自动化会话管理 |
| WebIntelligenceService | Web 搜索和知识检索 |
| CodeGenerationService | 代码生成和执行 |
| FirecrawlService | 网页抓取和内容提取 |
| QuotaService | 多租户配额管理 |
| RateLimitService | 令牌桶限流 |
| UpdateService | 上游项目更新检测 |

### 基础设施层

- **数据库**: PostgreSQL + SQLAlchemy (async) + Alembic 迁移
- **缓存**: Redis (消息总线、限流、缓存)
- **消息总线**: In-Memory / Redis 双模式
- **事件系统**: 自定义事件 + SSE 流式推送
- **WebSocket**: 桌面节点通信 + 实时更新
- **凭证管理**: 加密存储 API 密钥

## 桌面 Agent 节点架构

```
┌──────────────────┐      WebSocket (JWT + TLS)      ┌──────────────────┐
│   控制中心 (Server) │ ◄─────────────────────────────► │  边缘节点 (Client)  │
│                  │                                   │                  │
│  NodeRegistry    │  ◄── 注册/心跳                    │  Heartbeat       │
│  Scheduler       │  ──► 调度指令                     │  Executor        │
│  Grounding       │  ◄── 截图 + UI Tree               │  ScreenCapture   │
│                  │                                   │  UITree          │
│                  │                                   │  SecurityPolicy  │
└──────────────────┘                                   └──────────────────┘
```

**安全机制**：
- WebSocket 连接使用 JWT 认证 + TLS 加密
- 桌面节点执行操作的权限策略（白名单/黑名单）
- 敏感操作需用户确认（human-in-the-loop）
- 截图和 UI 树数据脱敏处理

## 多租户架构

```
┌──────────────────────────────────────────────┐
│              Tenant Isolation Layer           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │ Tenant A │  │ Tenant B │  │ Tenant C │      │
│  │ Agents:5 │  │ Agents:3 │  │ Agents:10│      │
│  │ Tokens:  │  │ Tokens:  │  │ Tokens:  │      │
│  │ 500K/day │  │ 200K/day │  │ 1M/day   │      │
│  └─────────┘  └─────────┘  └─────────┘      │
├──────────────────────────────────────────────┤
│              Quota Manager                    │
│  速率限制 | 资源配额 | 用量追踪 | 每日重置    │
└──────────────────────────────────────────────┘
```

- 每个租户独立的 Agent、Session、Workspace 配额
- 令牌桶算法实现速率限制（三级：tenant+endpoint / tenant-wide / endpoint-wide）
- 每日自动重置用量统计
- 支持动态配额调整

## 上游项目更新检测

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│AgentScope│  │ OpenWolf │  │ Agent-S  │  │ Firecrawl│
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │
     └─────────────┴──────┬──────┴─────────────┘
                          │
                   ┌──────▼──────┐
                   │  UpdateChecker│  (定时检查)
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │  UpdateMerger │  (安全合并)
                   └──────┬──────┘
                          │
              ┌───────────┴───────────┐
              │                       │
        ┌─────▼─────┐          ┌─────▼─────┐
        │  自动合并   │          │  冲突标记   │
        │ (SKPL目录) │          │ (共享目录)  │
        └───────────┘          └───────────┘
```

- SKPL 自有目录（desktop_node、firecrawl、skills 等）永不覆盖
- 共享目录（storage、router 等）合并时标记冲突
- 上游新增文件放入 staging 区
- 破坏性变更需人工审核

## 数据流

```
用户请求 → Nginx → Frontend (SPA)
                      │
                      ▼
              FastAPI Backend
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   Middleware     Service        Router
   (上下文/限流)   (业务逻辑)     (API端点)
        │             │             │
        └─────────────┼─────────────┘
                      ▼
              Storage / Model
              (PostgreSQL / Redis / LLM API)
```

## 技术栈总结

| 层级 | 技术 |
|------|------|
| 前端 | React 19, TypeScript 6, Vite 8, TailwindCSS 4, shadcn/ui |
| 后端 | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| 数据库 | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic |
| 缓存 | Redis 7 |
| AI | OpenAI, Anthropic, Gemini, DashScope, DeepSeek, Moonshot, Ollama, xAI |
| 部署 | Docker, Docker Compose, Kubernetes, GitHub Actions |
| 监控 | OpenTelemetry, Prometheus, Grafana |
| 测试 | Pytest, pytest-asyncio, pytest-cov, locust |
| 代码质量 | Ruff, MyPy, ESLint, Prettier |
| 许可证 | AGPL-3.0 |