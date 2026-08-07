# SKPL Agent API 参考

## 基础信息

- **Base URL**: `http://localhost:8000/api`
- **Content-Type**: `application/json`
- **认证**: 通过环境变量配置的 API 密钥 / JWT Token
- **响应格式**: JSON

## 健康检查

### GET /api/health

返回服务健康状态。

**响应示例**:
```json
{
  "status": "ok",
  "version": "2.0.5",
  "uptime": 3600
}
```

---

## Chat

### POST /api/chat/send

发送消息到 Agent 会话。

**请求体**:
```json
{
  "session_id": "abc123",
  "message": "分析这个项目",
  "agent_id": "default",
  "model": "gpt-4.1",
  "stream": true
}
```

### GET /api/chat/sessions/{session_id}/messages

获取会话消息历史。

**查询参数**: `limit` (默认 50), `cursor` (分页游标)

---

## Session

### GET /api/sessions

列出所有会话。

### POST /api/sessions

创建新会话。

**请求体**:
```json
{
  "name": "新会话",
  "agent_id": "default",
  "model": "gpt-4.1"
}
```

### DELETE /api/sessions/{session_id}

删除会话。

---

## Context（上下文管理）

### GET /api/context/{session_id}

获取当前会话的上下文聚合。

### POST /api/context/{session_id}/scan

触发项目扫描。

**请求体**:
```json
{
  "project_path": "/path/to/project",
  "scan_type": "full"
}
```

### GET /api/context/{session_id}/symbols

获取项目符号表。

**查询参数**: `query` (搜索关键词), `file_pattern` (文件过滤)

### GET /api/context/{session_id}/anatomy

获取项目结构概览。

---

## BugLog

### GET /api/buglog

列出 Bug 记录。

**查询参数**: `status` (open/closed), `severity` (low/medium/high/critical), `limit`

### POST /api/buglog

创建 Bug 记录。

**请求体**:
```json
{
  "title": "空指针异常",
  "description": "在调用 foo() 时发生",
  "severity": "high",
  "file_path": "src/main.py",
  "line_number": 42
}
```

### PUT /api/buglog/{bug_id}

更新 Bug 状态。

---

## Desktop Automation

### POST /api/desktop-automation/sessions

创建桌面自动化会话。

### GET /api/desktop-automation/sessions

列出活跃会话。

### POST /api/desktop-automation/sessions/{session_id}/tree

提取 UI 可访问性树。

**请求体**:
```json
{
  "show_all": false
}
```

### POST /api/desktop-automation/sessions/{session_id}/actions

派发桌面操作。

**请求体**:
```json
{
  "action_type": "click",
  "params": {
    "x": 100,
    "y": 200
  }
}
```

支持的操作类型：`click`, `double_click`, `right_click`, `type`, `hotkey`, `scroll`, `drag`, `screenshot`, `wait`

### POST /api/desktop-automation/sessions/{session_id}/screenshot

截图（返回 base64 PNG）。

### GET /api/desktop-automation/actions

列出可用操作。

---

## Web Intelligence

### POST /api/web-intelligence/search

执行 Web 搜索。

**请求体**:
```json
{
  "query": "Python 3.13 新特性",
  "engine": "auto",
  "max_results": 10
}
```

### POST /api/web-intelligence/research

启动深度研究任务。

**请求体**:
```json
{
  "topic": "Transformer 架构最新进展",
  "depth": "comprehensive",
  "max_sources": 20
}
```

### GET /api/web-intelligence/research/{task_id}

获取研究任务状态。

### GET /api/web-intelligence/engines

列出可用搜索引擎。

---

## Code Generation

### POST /api/code-generation/execute

执行代码生成任务。

**请求体**:
```json
{
  "prompt": "创建一个 Flask REST API",
  "language": "python",
  "sandbox": true
}
```

### GET /api/code-generation/results/{execution_id}

获取执行结果。

### POST /api/code-generation/run/python

在沙箱中执行 Python 代码。

### POST /api/code-generation/run/bash

在沙箱中执行 Bash 命令。

---

## Firecrawl

### POST /api/firecrawl/crawl

启动网页抓取。

**请求体**:
```json
{
  "url": "https://example.com",
  "mode": "crawl",
  "max_pages": 10
}
```

### GET /api/firecrawl/crawl/{crawl_id}

获取抓取状态。

### GET /api/firecrawl/crawls

列出抓取任务。

**查询参数**: `limit` (默认 50)

### POST /api/firecrawl/cancel

取消抓取。

**请求体**:
```json
{
  "crawl_id": "abc123"
}
```

### GET /api/firecrawl/config

获取 Firecrawl 配置。

### PUT /api/firecrawl/config

更新配置。

### GET /api/firecrawl/stats

获取使用统计。

---

## Quota（配额管理）

### GET /api/quota/tenants

列出所有租户配额。

### GET /api/quota/tenants/{tenant_id}

获取租户配额。

### PUT /api/quota/tenants/{tenant_id}

更新租户配额。

**请求体**:
```json
{
  "max_agents": 20,
  "max_tokens_per_day": 2000000,
  "max_api_requests_per_minute": 200
}
```

### GET /api/quota/tenants/{tenant_id}/usage

获取租户当前用量。

### GET /api/quota/tenants/{tenant_id}/status

获取租户所有资源配额状态。

### POST /api/quota/check

检查资源配额。

**请求体**:
```json
{
  "tenant_id": "default",
  "resource_type": "agents"
}
```

### GET /api/quota/stats

获取全局配额统计。

---

## Updates（更新检测）

### GET /api/updates/status

获取更新检测状态。

### POST /api/updates/check

立即检查上游更新。

### POST /api/updates/merge/{repo_name}

合并上游变更。

### POST /api/updates/rollback/{repo_name}

回滚合并。

### GET /api/updates/repos

列出跟踪的上游仓库。

### POST /api/updates/repos

添加上游仓库。

**请求体**:
```json
{
  "name": "new-repo",
  "url": "https://github.com/org/repo",
  "branch": "main"
}
```

### DELETE /api/updates/repos/{name}

移除上游仓库。

---

## 错误响应

所有 API 错误返回统一格式：

```json
{
  "error": {
    "code": "QUOTA_EXCEEDED",
    "message": "Agent 数量已达上限 (10)",
    "details": {
      "current": 10,
      "max": 10,
      "resource": "agents"
    }
  }
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 速率限制 |
| 500 | 服务器内部错误 |

### 速率限制

超限响应包含以下头：
- `X-RateLimit-Limit`: 限制值
- `X-RateLimit-Remaining`: 剩余次数
- `X-RateLimit-Reset`: 重置时间（Unix 时间戳）
- `Retry-After`: 建议重试等待秒数