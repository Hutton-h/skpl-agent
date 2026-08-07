# SKPL Agent 文档

## 快速导航

| 文档 | 说明 |
|------|------|
| [快速开始](getting_started.md) | 环境搭建和首次运行 |
| [架构设计](architecture.md) | 五层架构和模块划分 |
| [开发指南](development.md) | 本地开发环境配置 |
| [部署指南](deployment.md) | Docker/K8s 生产部署 |
| [API 参考](api-reference.md) | 完整 REST API 文档 |
| [配置参考](configuration.md) | 所有配置项说明 |
| [安全策略](security.md) | 安全模型和最佳实践 |
| [概念模型](concept_model.md) | 核心概念和数据模型 |
| [融合指南](fusion_guide.md) | 四个上游项目的融合设计 |
| [迁移指南](migration_guide.md) | 从 AgentScope 迁移 |
| [模块映射](module_map.md) | 各模块对应的上游项目 |
| [桌面节点指南](desktop_node_guide.md) | 桌面自动化节点部署 |

## 架构决策记录 (ADR)

| ADR | 标题 |
|-----|------|
| [ADR-0001](adr/0001-license-choice.md) | AGPL-3.0 许可证选择 |
| [ADR-0002](adr/0002-desktop-node-separation.md) | 桌面节点分离架构 |
| [ADR-0003](adr/0003-storage-strategy.md) | 存储策略 |

## 项目结构

```
skpl-agent/
├── backend/              # Python 后端 (FastAPI)
│   ├── src/skpl_agent/   # 核心代码
│   ├── tests/            # 测试
│   └── scripts/          # 工具脚本
├── frontend/             # React 前端
├── skills/               # 技能插件
├── desktop_node/         # 桌面自动化节点
├── deploy/               # 部署配置
│   ├── docker/           # Docker 配置
│   └── k8s/              # Kubernetes 配置
├── docs/                 # 文档
└── .github/              # CI/CD 工作流
```

## 四个上游项目

SKPL Agent 融合了以下四个开源项目：

| 项目 | 许可证 | 核心能力 |
|------|--------|----------|
| [AgentScope](https://github.com/modelscope/agentscope) | Apache 2.0 | 多 Agent 框架 |
| [OpenWolf](https://github.com/nicklausroach/openwolf) | AGPL-3.0 | 上下文管理 |
| [Agent-S](https://github.com/simular-ai/Agent-S) | Apache 2.0 | 桌面自动化 |
| [Firecrawl](https://github.com/mendableai/firecrawl) | AGPL-3.0/MIT | 网页抓取 |