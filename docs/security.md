# SKPL Agent 安全指南

## 认证与授权

### JWT 认证

- 桌面节点 WebSocket 连接使用 JWT Bearer Token 认证
- Token 包含节点 ID、租户 ID 和过期时间
- 默认过期时间：24 小时
- 生产环境必须配置强密钥：`openssl rand -hex 32`

### API 认证

- LLM API 密钥通过环境变量注入，不在代码中硬编码
- 支持密钥轮换（无需重启服务）
- 凭证存储使用加密（AES-256-GCM）

### 多租户隔离

- 租户通过 `X-Tenant-ID` 请求头识别
- 数据访问层按租户 ID 过滤
- 配额系统防止单租户资源耗尽
- 跨租户数据访问被中间件拦截

## 网络安全

### SSRF 防护

`SSRFProtection` 类执行以下检查：

- 协议白名单（仅 http/https）
- 内网 IP 黑名单（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16）
- 特殊主机名黑名单（localhost, metadata.google.internal 等）
- 可选 DNS 重绑定保护
- 可选域名白名单模式

### 速率限制

- 令牌桶算法，三级限制：
  - Tenant + Endpoint：最细粒度
  - Tenant-wide：租户级别
  - Endpoint-wide：全局端点级别
- 默认：100 请求/分钟/租户
- 超限返回 HTTP 429 + `Retry-After` 头

### WebSocket 安全

- 连接建立时验证 JWT（`wss://` 协议）
- 消息级权限检查
- 心跳超时自动断开（默认 30 秒）
- 最大连接数限制

## 桌面节点安全

### 权限模型

```
操作类型：
├── read_only     # 截图、UI树提取（低风险）
├── input         # 键盘/鼠标操作（中风险）
├── file_access   # 文件读写（高风险）
├── system        # 系统命令执行（最高风险）
└── browser       # 浏览器控制（高风险）
```

### 安全策略

- 白名单模式：仅允许预定义操作
- 敏感操作需用户确认（human-in-the-loop）
- 截图内容自动脱敏（密码字段、信用卡号）
- 操作日志完整记录，支持审计

### 部署安全

- 桌面节点只能通过加密 WebSocket 连接服务器
- 节点证书由服务器签发
- 节点 ID 与机器指纹绑定
- 离线节点自动注销

## 数据安全

### 敏感数据

| 数据类型 | 存储方式 | 加密 |
|----------|----------|------|
| API 密钥 | 环境变量 / Secrets Manager | 是 |
| 用户消息 | PostgreSQL | 可选 |
| 截图 | 临时文件 | 传输加密 |
| Token 用量 | PostgreSQL | 否 |
| Bug 日志 | SQLite / PostgreSQL | 否 |

### 数据保留

- 会话数据：默认 30 天
- 截图：处理后立即删除
- 审计日志：1 年
- Token 用量：永久保留（聚合）

## 依赖安全

- 定期扫描依赖漏洞（`pip-audit`、`npm audit`）
- 上游项目更新检测（每日检查 4 个上游仓库）
- 自动合并安全补丁
- 破坏性变更需人工审核

## 生产环境检查清单

- [ ] 修改所有默认密钥和密码
- [ ] 启用 HTTPS（TLS 1.2+）
- [ ] 配置防火墙规则
- [ ] 限制数据库端口仅本地访问
- [ ] 启用速率限制
- [ ] 配置日志聚合
- [ ] 设置监控告警
- [ ] 配置自动备份
- [ ] 运行安全扫描
- [ ] 审查访问控制策略
- [ ] 配置 WAF（Web 应用防火墙）
- [ ] 启用审计日志

## 漏洞报告

发现安全漏洞请发送邮件至 `security@skpl-agent.dev`，不要在 GitHub Issue 公开披露。我们将在 48 小时内响应。采用 [Temporal Communications Security Agreement](https://temporal.io/security) 流程。我们目前不提供漏洞赏金计划。

## 许可证合规

- 项目主体：AGPL-3.0
- AgentScope 上游：Apache 2.0（兼容）
- OpenWolf 上游：MIT（兼容）
- Agent-S 上游：MIT（兼容）
- Firecrawl 上游：AGPL-3.0（兼容）

所有上游许可证声明保留在 `LICENSE` 文件中。修改和分发须遵守 AGPL-3.0 条款。