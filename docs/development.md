# SKPL Agent 开发指南

## 项目结构

```
skpl-agent/
├── backend/
│   ├── src/skpl_agent/          # 后端源码
│   │   ├── agent/               # Agent 核心引擎
│   │   ├── model/               # 11 个 LLM 模型后端
│   │   ├── tool/                # 工具系统
│   │   ├── middleware/           # Agent 中间件（tracing、memory、rag）
│   │   ├── workspace/           # 7 种沙箱后端
│   │   ├── context/             # 上下文管理（OpenWolf）
│   │   ├── app/                 # FastAPI 应用层
│   │   │   ├── _router/         # API 路由
│   │   │   ├── _service/        # 业务逻辑服务
│   │   │   ├── _middleware/     # HTTP 中间件
│   │   │   ├── _manager/        # 管理器（调度、取消）
│   │   │   ├── _ws/             # WebSocket 处理
│   │   │   ├── _security/       # SSRF 防护
│   │   │   ├── middleware/      # 应用中间件
│   │   │   ├── storage/         # 存储后端（SQL/Redis/S3）
│   │   │   └── message_bus/     # 消息总线
│   │   ├── desktop_node/        # 桌面 Agent 节点
│   │   ├── desktop_automation/  # 桌面自动化引擎
│   │   ├── firecrawl/           # Firecrawl 集成
│   │   ├── web_intelligence/    # Web 智能研究
│   │   ├── code_generation/     # 代码生成
│   │   ├── updates/             # 上游更新检测
│   │   ├── credential/          # 凭证管理
│   │   ├── embedding/           # 嵌入模型
│   │   ├── rag/                 # RAG 管道
│   │   ├── skill/               # Skill 加载器
│   │   ├── event/               # 事件系统
│   │   ├── formatter/           # 模型格式化器
│   │   ├── mcp/                 # MCP 客户端
│   │   ├── message/             # 消息系统
│   │   ├── state/               # 状态管理
│   │   └── config.py            # 统一配置
│   ├── tests/                   # 测试
│   │   ├── unit/                # 单元测试
│   │   ├── integration/         # 集成测试
│   │   ├── parity/              # 对等测试
│   │   └── performance/         # 性能测试
│   └── scripts/                 # 工具脚本
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # 通用组件
│   │   ├── api/                 # API 客户端
│   │   ├── hooks/               # 自定义 Hooks
│   │   └── i18n/                # 国际化
│   └── package.json
├── skills/                      # Skill 模块
│   ├── firecrawl/tools/         # 网页抓取工具
│   ├── context/tools/           # 上下文管理工具
│   └── desktop/tools/           # 桌面自动化工具
├── docs/                        # 文档
├── deploy/                      # 部署配置
│   ├── k8s/                     # Kubernetes
│   └── nginx.conf               # Nginx 配置
├── .github/workflows/           # CI/CD
├── Dockerfile.backend           # 后端镜像
├── Dockerfile.frontend          # 前端镜像
├── docker-compose.yml           # 本地编排
├── Makefile                     # 统一命令
└── pyproject.toml               # 项目配置
```

## 开发环境设置

### 后端

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
make test

# 代码检查
make lint
make types
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev        # 开发服务器
pnpm build      # 生产构建
pnpm lint       # 代码检查
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `make dev` | 启动后端开发服务器 |
| `make frontend-dev` | 启动前端开发服务器 |
| `make test` | 运行所有测试 |
| `make test-unit` | 运行单元测试 |
| `make test-cov` | 运行测试 + 覆盖率 |
| `make lint` | 后端代码检查 |
| `make format` | 后端代码格式化 |
| `make types` | 类型检查 |
| `make migrate` | 运行数据库迁移 |
| `make docker-build` | 构建 Docker 镜像 |
| `make docker-up` | 启动 Docker 服务 |
| `make check-updates` | 检查上游更新 |

## 代码规范

### Python

- Python 3.11+ 语法
- 类型注解：所有公共 API 必须标注
- 文档字符串：Google 风格
- 行长度：100 字符
- 格式化：Ruff
- 类型检查：MyPy
- 使用 `from __future__ import annotations` 延迟求值

### TypeScript

- TypeScript 6 严格模式
- 格式化：ESLint + Prettier
- 组件：函数组件 + Hooks
- 样式：TailwindCSS 4

## 添加新功能

### 添加新的模型后端

1. 在 `model/` 下创建 `_provider/` 目录
2. 实现 `_model.py`（继承 `ChatModelBase`）
3. 在 `_models/` 添加 YAML 模型定义
4. 在 `formatter/` 添加消息格式化器
5. 更新 `pyproject.toml` 可选依赖

### 添加新的 API 端点

1. 在 `app/_service/` 创建服务类
2. 在 `app/_router/` 创建路由
3. 在 `app/_router/_schema/` 创建 Pydantic 模型
4. 在 `app/_app.py` 注册路由
5. 前端在 `api/` 创建 API 客户端
6. 前端在 `pages/` 创建页面

### 添加新的 Skill

1. 在 `skills/` 下创建 `skill_name/tools/` 目录
2. 实现工具类（参考 `skills/firecrawl/tools/`）
3. 在 `skills/skill_name/tools/__init__.py` 导出
4. 在 `pyproject.toml` 注册入口点

## 测试

```bash
# 所有测试
pytest backend/tests -v

# 跳过慢速测试
pytest backend/tests -v -m "not slow"

# 仅单元测试
pytest backend/tests/unit -v

# 仅集成测试
pytest backend/tests/integration -v

# 覆盖率报告
pytest backend/tests --cov=backend/src/skpl_agent --cov-report=html

# 性能测试
pytest backend/tests/performance -v
```

## 数据库迁移

```bash
# 创建新迁移
make migrate-create MESSAGE="add new table"

# 执行迁移
make migrate

# 回滚
make migrate-downgrade

# 查看历史
make migrate-history
```

## 调试

```bash
# 启动后端（调试模式）
SKPL_LOG_LEVEL=DEBUG uvicorn skpl_agent.app._app:app --reload

# 查看日志
tail -f logs/skpl-agent.log

# Docker 日志
docker compose logs -f backend
```