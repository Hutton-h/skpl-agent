# 贡献指南

感谢你对 SKPL Agent 的关注！本文档帮助你了解如何参与项目开发。

## 行为准则

本项目遵循 [Contributor Covenant](https://www.contributor-covenant.org/) 行为准则。参与即表示你同意遵守其条款。

## 如何贡献

### 报告 Bug

1. 在 GitHub Issues 中搜索是否已有相同问题
2. 使用 Bug Report 模板创建新 Issue
3. 提供：复现步骤、预期行为、实际行为、环境信息

### 提出功能建议

1. 在 Issues 中搜索是否已有类似建议
2. 使用 Feature Request 模板
3. 描述：使用场景、期望行为、替代方案

### 提交代码

1. **Fork** 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 编写代码和测试
4. 确保代码通过检查：`make lint && make test`
5. 提交更改：`git commit -m "feat: add your feature"`
6. 推送到分支：`git push origin feature/your-feature`
7. 创建 Pull Request

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/skpl-agent/skpl-agent.git
cd skpl-agent

# 安装依赖
pip install -e ".[dev]"
cd frontend && npm install && cd ..

# 运行测试
make test
make lint
```

## 代码规范

### Python

- 遵循 [PEP 8](https://peps.python.org/pep-0008/)
- 使用 Ruff 进行格式化和 lint
- 使用 MyPy 进行类型检查
- 所有公开函数需要 docstring
- 测试覆盖率不低于 80%

### TypeScript/React

- 使用 ESLint + Prettier
- 遵循 React 最佳实践
- 组件使用函数式风格 + Hooks
- 使用 TypeScript 严格模式

### 提交信息

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 添加新功能
fix: 修复 Bug
docs: 文档更新
test: 测试相关
refactor: 重构
chore: 构建/工具变更
```

## 分支策略

- `main` — 稳定版本，只接受 PR 合并
- `develop` — 开发分支
- `feature/*` — 功能分支
- `fix/*` — 修复分支

## 测试

```bash
# 单元测试
pytest backend/tests/unit/

# 集成测试
pytest backend/tests/integration/

# 全部测试
make test

# 覆盖率报告
pytest --cov=skpl_agent --cov-report=html
```

## 许可证

贡献的代码将采用 AGPL-3.0 许可证。详见 [LICENSE](../LICENSE)。