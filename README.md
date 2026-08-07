# SKPL Agent

**Super Knowledge & Process Learning Agent Platform**

SKPL Agent 是一个多 Agent AI 平台，融合了四个上游项目的核心能力。

[![CI](https://github.com/skpl-agent/skpl-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/skpl-agent/skpl-agent/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

## 上游项目

| 项目 | 许可证 | 集成的能力 |
|------|--------|-----------|
| [AgentScope](https://github.com/agentscope-ai/agentscope) | Apache 2.0 | 多 Agent 框架、11 个模型后端、7 种沙箱、RAG、记忆、完整前后端 |
| [OpenWolf](https://github.com/nicklausroach/OpenWolf) | AGPL-3.0 | 自动上下文管理、项目解剖扫描、符号提取、Bug 追踪、Token 优化 |
| [Agent-S](https://github.com/simular-ai/Agent-S) | AGPL-3.0 | 桌面自动化、GUI 元素检测、键盘鼠标控制、UI 树提取 |
| [Firecrawl](https://github.com/mendableai/firecrawl) | AGPL-3.0 | 网页抓取、内容提取、站点地图、搜索集成 |

## 架构

```
控制中心 (Server) ←──WebSocket (JWT+TLS)──→ 桌面 Agent 节点 (Local)
      │
      ├── FastAPI REST API
      ├── 11 × LLM 模型后端
      ├── 7 × 沙箱后端
      ├── 4 × 向量数据库
      ├── 3 × 长期记忆方案
      ├── 上下文管理 (OpenWolf)
      ├── 桌面自动化 (Agent-S)
      ├── 网页抓取 (Firecrawl)
      ├── 多租户配额管理
      └── 上游更新检测
```

## 快速开始

### Docker Compose（推荐）

```bash
git clone https://github.com/skpl-agent/skpl-agent.git
cd skpl-agent
cp .env.example .env
# 编辑 .env 填入 API 密钥
docker compose --profile full up -d
```

### 本地开发

```bash
pip install -e ".[dev]"
make dev              # 后端 http://localhost:8000
make frontend-dev     # 前端 http://localhost:5173
```

## 文档

| 文档 | 说明 |
|------|------|
| [架构设计](docs/architecture.md) | 五层架构、桌面节点、多租户设计 |
| [API 参考](docs/api-reference.md) | 完整 REST API 文档 |
| [部署指南](docs/deployment.md) | Docker、Kubernetes 部署 |
| [安全指南](docs/security.md) | 认证、授权、SSRF 防护 |
| [开发指南](docs/development.md) | 项目结构、开发规范 |
| [配置参考](docs/configuration.md) | 所有环境变量说明 |

## 常用命令

| 命令 | 说明 |
|------|------|
| `make dev` | 启动后端开发服务器 |
| `make frontend-dev` | 启动前端开发服务器 |
| `make test` | 运行所有测试 |
| `make lint` | 代码检查 |
| `make format` | 代码格式化 |
| `make docker-up` | 启动 Docker 服务 |
| `make migrate` | 数据库迁移 |
| `make check-updates` | 检查上游更新 |

## 许可证

SKPL Agent 采用 **AGPL-3.0** 许可证。上游项目保留原始许可证声明，详见 [LICENSE](LICENSE)。