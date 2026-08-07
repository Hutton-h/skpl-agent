# SKPL Agent 部署指南

## 快速开始

### 环境要求

- Docker 24+ & Docker Compose v2
- Python 3.11+
- Node.js 22+ & pnpm 11
- PostgreSQL 16 (Docker 部署时自动提供)
- Redis 7 (Docker 部署时自动提供)

### Docker Compose 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/skpl-agent/skpl-agent.git
cd skpl-agent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥和其他配置

# 3. 启动所有服务
docker compose --profile full up -d

# 4. 运行数据库迁移
docker compose exec backend alembic upgrade head

# 5. 访问
# Frontend: http://localhost
# Backend API: http://localhost:8000
# pgAdmin: http://localhost:5050 (仅在 full profile 下)
```

### 最小部署（仅后端 + 数据库）

```bash
docker compose --profile minimal up -d
```

### 本地开发部署

```bash
# 1. 安装后端依赖
pip install -e ".[dev]"

# 2. 安装前端依赖
cd frontend && pnpm install && cd ..

# 3. 启动数据库
docker compose up -d postgres redis

# 4. 运行迁移
make migrate

# 5. 启动后端（终端1）
make dev
# Backend: http://localhost:8000

# 6. 启动前端（终端2）
make frontend-dev
# Frontend: http://localhost:5173
```

## Kubernetes 部署

```bash
# 1. 创建命名空间和资源
kubectl apply -f deploy/k8s/skpl-agent.yaml

# 2. 查看 Pod 状态
kubectl -n skpl-agent get pods

# 3. 端口转发访问
kubectl -n skpl-agent port-forward svc/skpl-frontend 8080:80

# 4. 配置 Ingress（可选）
# 编辑 deploy/k8s/skpl-agent.yaml 取消 Ingress 部分的注释
# 修改域名和 TLS 配置后重新 apply
```

## 配置说明

### 必需配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SKPL_SECRET_KEY` | 应用密钥（生产环境必须修改） | `change-me-in-production` |
| `SKPL_JWT_SECRET` | JWT 签名密钥 | `change-me-in-production` |
| `SKPL_DB_PASSWORD` | 数据库密码 | `skpl_secret` |

### LLM API 密钥

至少配置一个 LLM 提供商：

| 变量 | 提供商 |
|------|--------|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic Claude |
| `DASHSCOPE_API_KEY` | 阿里 DashScope |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `GEMINI_API_KEY` | Google Gemini |
| `MOONSHOT_API_KEY` | Moonshot/Kimi |
| `XAI_API_KEY` | xAI Grok |

### 可选配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SKPL_LOG_LEVEL` | 日志级别 | `INFO` |
| `SKPL_BACKEND_PORT` | 后端端口 | `8000` |
| `SKPL_FRONTEND_PORT` | 前端端口 | `80` |
| `FIRECRAWL_API_KEY` | Firecrawl API 密钥 | - |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry 端点 | - |

## 桌面节点部署

桌面 Agent 节点需要直接运行在用户机器上（不能容器化）：

```bash
# 安装桌面依赖
pip install -e ".[desktop]"

# 启动桌面节点
make desktop-node
# 或
python -m skpl_agent.desktop_node --server ws://your-server:8000/ws/desktop
```

## 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/api/health

# 前端健康检查
curl http://localhost/
```

## 日志

```bash
# Docker Compose 日志
docker compose logs -f backend
docker compose logs -f frontend

# K8s 日志
kubectl -n skpl-agent logs -f deployment/skpl-backend
```

## 备份

```bash
# PostgreSQL 备份
docker compose exec postgres pg_dump -U skpl skpl_agent > backup.sql

# 恢复
docker compose exec -T postgres psql -U skpl skpl_agent < backup.sql
```

## 升级

```bash
# 拉取最新镜像
docker compose pull

# 重新部署
docker compose up -d --remove-orphans

# 运行数据库迁移
docker compose exec backend alembic upgrade head
```

## 安全建议

1. 生产环境必须修改所有默认密钥和密码
2. 使用 `openssl rand -hex 32` 生成强随机密钥
3. 启用 HTTPS（通过反向代理或 Ingress TLS）
4. 限制 PostgreSQL 和 Redis 端口仅本地访问
5. 定期更新依赖和基础镜像
6. 配置防火墙规则
7. 使用 secrets manager 管理敏感信息（K8s Secrets / Vault）