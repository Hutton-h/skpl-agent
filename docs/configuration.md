# SKPL Agent 配置参考

## 配置系统

SKPL Agent 使用 Pydantic Settings 进行配置管理，支持环境变量、`.env` 文件和默认值。

配置类位于 `backend/src/skpl_agent/config.py`。

## CoreSettings（核心配置）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SKPL_HOST` | str | `0.0.0.0` | 服务监听地址 |
| `SKPL_PORT` | int | `8000` | 服务端口 |
| `SKPL_LOG_LEVEL` | str | `INFO` | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `SKPL_SECRET_KEY` | str | - | 应用密钥（生产环境必须修改） |
| `SKPL_JWT_SECRET` | str | - | JWT 签名密钥 |
| `SKPL_DATA_DIR` | str | `./data` | 数据存储目录 |
| `SKPL_DEBUG` | bool | `False` | 调试模式 |

## ContextSettings（上下文配置）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SKPL_CONTEXT_MAX_FILES` | int | `1000` | 单次扫描最大文件数 |
| `SKPL_CONTEXT_MAX_FILE_SIZE_MB` | int | `5` | 单个文件最大大小（MB） |
| `SKPL_CONTEXT_SCAN_INTERVAL` | int | `300` | 自动扫描间隔（秒） |
| `SKPL_CONTEXT_STORE_BACKEND` | str | `sqlite` | 存储后端 (sqlite/json) |
| `SKPL_CONTEXT_TOKEN_BUDGET` | int | `100000` | 上下文 Token 预算 |
| `SKPL_CONTEXT_WASTE_THRESHOLD` | float | `0.3` | 浪费检测阈值 |

## DesktopSettings（桌面配置）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SKPL_DESKTOP_WS_URL` | str | `ws://localhost:8000` | WebSocket 连接地址 |
| `SKPL_DESKTOP_HEARTBEAT_INTERVAL` | int | `30` | 心跳间隔（秒） |
| `SKPL_DESKTOP_HEARTBEAT_TIMEOUT` | int | `90` | 心跳超时（秒） |
| `SKPL_DESKTOP_MAX_NODES` | int | `10` | 最大桌面节点数 |
| `SKPL_DESKTOP_SCREENSHOT_QUALITY` | int | `80` | 截图质量 (1-100) |
| `SKPL_DESKTOP_GROUNDING_ENABLED` | bool | `False` | 启用 UI 元素检测 |
| `SKPL_DESKTOP_SECURITY_LEVEL` | str | `standard` | 安全级别 (permissive/standard/strict) |

## WebSettings（Web 配置）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SKPL_WEB_MAX_CONCURRENT_CRAWLS` | int | `3` | 最大并发抓取数 |
| `SKPL_WEB_RATE_LIMIT_PER_MINUTE` | int | `10` | 每分钟请求限制 |
| `SKPL_WEB_DEFAULT_MAX_PAGES` | int | `50` | 默认最大页数 |
| `SKPL_WEB_TIMEOUT_SECONDS` | int | `300` | 请求超时（秒） |
| `SKPL_WEB_RESPECT_ROBOTS_TXT` | bool | `True` | 遵守 robots.txt |
| `SKPL_WEB_USER_AGENT` | str | `SKPL-Agent-Firecrawl/0.1` | User-Agent |

## UpdateSettings（更新配置）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SKPL_UPDATE_CHECK_INTERVAL_HOURS` | int | `6` | 检查间隔（小时） |
| `SKPL_UPDATE_AUTO_MERGE` | bool | `False` | 自动合并安全更新 |
| `SKPL_UPDATE_NOTIFY_ON_UPDATE` | bool | `True` | 有更新时通知 |
| `SKPL_UPDATE_WEBHOOK_URL` | str | `""` | 通知 Webhook URL |

## QuotaSettings（配额配置）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SKPL_QUOTA_MAX_AGENTS` | int | `10` | 每租户最大 Agent 数 |
| `SKPL_QUOTA_MAX_SESSIONS` | int | `50` | 每租户最大会话数 |
| `SKPL_QUOTA_MAX_WORKSPACES` | int | `5` | 每租户最大工作空间数 |
| `SKPL_QUOTA_MAX_DESKTOP_NODES` | int | `3` | 每租户最大桌面节点数 |
| `SKPL_QUOTA_MAX_WEB_REQUESTS_PER_DAY` | int | `10000` | 每日最大 Web 请求 |
| `SKPL_QUOTA_MAX_TOKENS_PER_DAY` | int | `1000000` | 每日最大 Token 数 |
| `SKPL_QUOTA_MAX_API_REQUESTS_PER_MINUTE` | int | `100` | 每分钟最大 API 请求 |
| `SKPL_QUOTA_MAX_STORAGE_MB` | int | `1024` | 每租户最大存储（MB） |

## 数据库配置

| 变量 | 说明 |
|------|------|
| `SKPL_DB_URL` | 数据库连接字符串（完整 URL） |
| `SKPL_DB_USER` | 数据库用户名 |
| `SKPL_DB_PASSWORD` | 数据库密码 |
| `SKPL_DB_NAME` | 数据库名称 |
| `SKPL_DB_HOST` | 数据库主机 |
| `SKPL_DB_PORT` | 数据库端口 |

**连接字符串格式**:
```
postgresql+asyncpg://user:password@host:port/database
```

## Redis 配置

| 变量 | 说明 |
|------|------|
| `SKPL_REDIS_URL` | Redis 连接字符串 |

**连接字符串格式**:
```
redis://host:port/db
```

## LLM API 密钥

| 变量 | 提供商 |
|------|--------|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `DASHSCOPE_API_KEY` | 阿里云 DashScope |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `GEMINI_API_KEY` | Google Gemini |
| `MOONSHOT_API_KEY` | Moonshot/Kimi |
| `XAI_API_KEY` | xAI Grok |
| `OLLAMA_HOST` | Ollama 本地服务地址 |

## Firecrawl 配置

| 变量 | 说明 |
|------|------|
| `FIRECRAWL_API_KEY` | Firecrawl API 密钥 |
| `FIRECRAWL_API_ENDPOINT` | API 端点（默认 https://api.firecrawl.dev） |

## 可观测性配置

| 变量 | 说明 |
|------|------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry Collector 端点 |
| `OTEL_SERVICE_NAME` | 服务名称（默认 skpl-agent-backend） |
| `OTEL_EXPORTER_OTLP_HEADERS` | OTLP 导出器自定义头 |

## 配置优先级

1. 命令行参数
2. 环境变量
3. `.env` 文件
4. 默认值

## 生产环境 .env 示例

```bash
# 安全（必须修改）
SKPL_SECRET_KEY=a1b2c3d4e5f6...（openssl rand -hex 32）
SKPL_JWT_SECRET=f6e5d4c3b2a1...（openssl rand -hex 32）

# 数据库
SKPL_DB_URL=postgresql+asyncpg://skpl:strong_password@postgres:5432/skpl_agent

# Redis
SKPL_REDIS_URL=redis://redis:6379/0

# 日志
SKPL_LOG_LEVEL=WARNING

# LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# 配额
SKPL_QUOTA_MAX_TOKENS_PER_DAY=5000000
SKPL_QUOTA_MAX_API_REQUESTS_PER_MINUTE=200

# 更新
SKPL_UPDATE_CHECK_INTERVAL_HOURS=12
SKPL_UPDATE_AUTO_MERGE=false

# 可观测性
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```