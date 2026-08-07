# 变更日志

## [0.1.0] — 2026-07-27

### 新增

#### Phase 0: 基础搭建
- 项目骨架：`backend/`、`frontend/`、`skills/`、`deploy/`、`docs/` 目录结构
- Python 后端：FastAPI + Pydantic Settings + Uvicorn
- React 前端：React 19 + TypeScript 6 + TailwindCSS 4 + shadcn/ui
- Docker Compose 开发环境：PostgreSQL 16 + Redis 7 + Backend + Frontend
- AGPL-3.0 许可证 + 上游项目许可证声明

#### Phase 1: OpenWolf 上下文集成
- 代码解剖扫描器：Tree-sitter 符号提取 + 正则降级
- 双模式解剖存储：SQLite (生产) + JSON (轻量)
- 跨进程文件锁：并发安全的数据访问
- Token 估算器：支持 tiktoken 精确计数和字符比例估算
- Token 账本：预算管理和超额检测
- Token 浪费检测：重复读取、冗余上下文、重复输出
- Bug 日志：Jaccard 相似度去重
- Cerebrum 大脑：Agent 状态持久化
- 7 个生命周期钩子：on_session_start / before_agent_invoke / after_agent_invoke / on_tool_call / on_tool_result / on_error / on_session_end
- 会话上下文管理器：统一编排所有子系统
- 敏感内容过滤器：PII 检测
- 上下文事件发射器：实时事件流
- 降级策略：4 级回退 (缓存 → 启发式 → 注释提取 → 空上下文)
- 外部适配器：Claude Code / Codex / Cursor
- 上下文中间件：FastAPI 中间件集成

#### Phase 2: Agent-S 桌面自动化
- ACI 自动化控制接口：Windows / macOS / Linux 三平台
- ACI 工厂模式：自动平台检测
- 桌面操作执行器：Token Bucket 速率限制
- UI-TARS 定位模型：视觉 grounding
- OCR 定位：EasyOCR 集成
- 坐标定位：简单坐标映射
- 定位服务：统一 grounding 接口
- BBON 服务：浏览器基础操作
- 桌面工具：AgentScope 工具集成
- 桌面权限：访问控制
- 桌面 WebSocket：节点注册 + 心跳 + 消息路由
- 桌面调度器：任务优先级调度
- 桌面节点 CLI：独立节点进程
- 前端节点状态面板

#### Phase 3: Firecrawl 技能接入
- Firecrawl 技能插件：6 个工具 (scrape / crawl / search / map / extract / parse)
- HTTP 客户端：自动重试 + 指数退避 + 超时处理
- Pydantic Schema：完整请求/响应模型
- MCP 配置：JSON Schema 工具定义
- SSRF 防护：内网 IP / localhost / DNS 重绑定 / 危险协议
- 域名速率限制：滑动窗口令牌桶
- 服务层：FirecrawlService 完整 CRUD

#### Phase 4: 持续更新检测
- 上游源配置：4 个仓库 (AgentScope / OpenWolf / Agent-S / Firecrawl)
- 更新管理器：APScheduler 定时检查
- 更新服务：检查 / 合并 / 回滚 / 仓库管理
- CLI 更新检查脚本：JSON / Text / GitHub Issue 输出
- CI 定时检查：每日自动检查 + 自动创建 Issue
- 前端更新状态面板

#### Phase 5: 部署与运维
- Docker 三件套：Backend / Frontend / Desktop Node
- Kubernetes 完整部署：PostgreSQL + Redis + Backend + Frontend + Ingress + HPA + Desktop Node StatefulSet
- 7 个 CI/CD 工作流：test / lint / security-scan / e2e / docker-build / bundle-analyze / update-check
- Dependabot 配置：pip + npm + Docker + GitHub Actions
- Pre-commit hooks：文件卫生 + Ruff + MyPy + detect-secrets
- 10 篇文档：README / architecture / development / deployment / API / security / contributing / changelog / configuration / getting_started
- 3 篇 ADR：许可证选择 / 桌面节点分离 / 存储策略
- 前端优化：React.lazy + Suspense + Vite manualChunks
- 前端组件：TokenUsage / BugTracker / NodeStatus / UpdateStatus

### 技术栈

- **后端**：Python 3.12+ / FastAPI / Pydantic v2 / SQLAlchemy 2.0 / APScheduler / OpenTelemetry
- **前端**：React 19 / TypeScript 6 / TailwindCSS 4 / Vite 8 / shadcn/ui
- **基础设施**：PostgreSQL 16 / Redis 7 / Docker / Kubernetes
- **测试**：pytest / Playwright / pytest-asyncio / pytest-cov
- **CI/CD**：GitHub Actions / Dependabot / Pre-commit

### 许可证

AGPL-3.0，包含上游项目许可证声明：
- AgentScope: Apache 2.0
- OpenWolf: AGPL-3.0
- Agent-S: Apache 2.0
- Firecrawl: AGPL-3.0 / MIT