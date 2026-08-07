"""
AgentShield — Agent 安全扫描模块

扫描 Agent 的系统提示词和配置，检测潜在的安全风险、敏感信息泄露、
权限过度授予等问题。集成到管理面板的安全审计页面。

Usage:
    from skpl_agent.app._security.agent_shield import AgentShield
    
    shield = AgentShield()
    results = await shield.scan_agent(agent_config)
    print(results.risk_level)  # low, medium, high, critical
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ScanRule:
    """扫描规则"""
    id: str
    category: str
    description: str
    severity: RiskLevel
    pattern: str | None = None
    check_fn: str | None = None  # 自定义检查函数名


@dataclass
class ScanFinding:
    """扫描发现"""
    rule_id: str
    category: str
    description: str
    severity: RiskLevel
    evidence: str = ""
    recommendation: str = ""


@dataclass
class ScanResult:
    """扫描结果"""
    agent_name: str
    total_findings: int
    risk_level: RiskLevel
    findings: list[ScanFinding] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    
    @property
    def passed(self) -> bool:
        return self.risk_level in (RiskLevel.LOW,)


# ── 扫描规则定义 ──────────────────────────────────────────

DEFAULT_RULES: list[ScanRule] = [
    # ── 敏感信息泄露 ──
    ScanRule(
        id="SHIELD-001",
        category="sensitive_data",
        description="系统提示词中包含 API Key 或 Token",
        severity=RiskLevel.CRITICAL,
        pattern=r"(?i)(api[_-]?key|api[_-]?secret|access[_-]?token)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?",
    ),
    ScanRule(
        id="SHIELD-002",
        category="sensitive_data",
        description="系统提示词中包含密码字段",
        severity=RiskLevel.CRITICAL,
        pattern=r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"].+?['\"]",
    ),
    ScanRule(
        id="SHIELD-003",
        category="sensitive_data",
        description="系统提示词中包含私钥内容",
        severity=RiskLevel.CRITICAL,
        pattern=r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
    ),
    
    # ── 权限过度授予 ──
    ScanRule(
        id="SHIELD-004",
        category="privilege_escalation",
        description="Agent 被授予执行任意 Shell 命令的权限",
        severity=RiskLevel.HIGH,
        pattern=r"(?i)(可以|允许|能够|run|execute|允许执行)\s*(任意|任何|所有|all|any)\s*(shell|bash|命令|command)",
    ),
    ScanRule(
        id="SHIELD-005",
        category="privilege_escalation",
        description="Agent 权限模式设置为 bypass（无限制）",
        severity=RiskLevel.HIGH,
        check_fn="check_permission_bypass",
    ),
    
    # ── 提示词注入风险 ──
    ScanRule(
        id="SHIELD-006",
        category="prompt_injection",
        description="系统提示词中缺少防止注入的指令",
        severity=RiskLevel.MEDIUM,
        pattern=r"(?i)(忽略|ignore|override|覆盖|绕过)\s*(之前|上面|above|previous|系统|system)",
    ),
    ScanRule(
        id="SHIELD-007",
        category="prompt_injection",
        description="系统提示词允许用户修改系统指令",
        severity=RiskLevel.HIGH,
        pattern=r"(?i)(用户|user)\s*(可以|can|may)\s*(修改|改变|更改|modify|change|override)\s*(系统|system)\s*(提示|指令|prompt|instruction)",
    ),
    
    # ── 数据泄露风险 ──
    ScanRule(
        id="SHIELD-008",
        category="data_exfiltration",
        description="Agent 可以向外部 URL 发送数据",
        severity=RiskLevel.MEDIUM,
        pattern=r"(?i)(发送|上传|upload|send|post)\s*(数据|文件|结果|data|file|result)\s*(到|给|to)\s*(http|外部|external|远程|remote)",
    ),
    ScanRule(
        id="SHIELD-009",
        category="data_exfiltration",
        description="Agent 被允许访问网络文件系统",
        severity=RiskLevel.MEDIUM,
        pattern=r"(?i)(访问|读取|read|access)\s*(网络|远程|remote|network)\s*(文件|file|目录|directory)",
    ),
    
    # ── 工具滥用风险 ──
    ScanRule(
        id="SHIELD-010",
        category="tool_abuse",
        description="Agent 工具数量超过 20 个，增加攻击面",
        severity=RiskLevel.LOW,
        check_fn="check_tool_count",
    ),
    ScanRule(
        id="SHIELD-011",
        category="tool_abuse",
        description="Agent 具有文件系统写入权限",
        severity=RiskLevel.MEDIUM,
        pattern=r"(?i)(写入|write|create|delete|删除|创建)\s*(文件|file|目录|directory)",
    ),
]


class AgentShield:
    """Agent 安全扫描器"""
    
    def __init__(self, rules: list[ScanRule] | None = None):
        self._rules = rules or DEFAULT_RULES
    
    async def scan_agent(self, agent_config: dict[str, Any]) -> ScanResult:
        """扫描 Agent 配置，返回安全审计结果
        
        Args:
            agent_config: Agent 配置字典，包含 system_prompt, tools, permission_mode 等
        
        Returns:
            ScanResult 包含所有发现和建议
        """
        name = agent_config.get("name", "Unknown")
        system_prompt = agent_config.get("system_prompt", "")
        tools = agent_config.get("tools", [])
        permission_mode = agent_config.get("permission_mode", "default")
        
        findings: list[ScanFinding] = []
        
        for rule in self._rules:
            if rule.pattern and system_prompt:
                matches = re.findall(rule.pattern, system_prompt, re.IGNORECASE)
                if matches:
                    evidence = str(matches[:3]) if len(matches) > 1 else str(matches[0]) if isinstance(matches[0], str) else str(matches[0][0])
                    findings.append(ScanFinding(
                        rule_id=rule.id,
                        category=rule.category,
                        description=rule.description,
                        severity=rule.severity,
                        evidence=evidence[:200],
                        recommendation=self._get_recommendation(rule),
                    ))
            
            if rule.check_fn:
                result = await self._run_check(rule, agent_config)
                if result:
                    findings.append(result)
        
        # 计算风险等级
        risk_level = self._calculate_risk(findings)
        categories = {}
        for f in findings:
            categories[f.category] = categories.get(f.category, 0) + 1
        
        return ScanResult(
            agent_name=name,
            total_findings=len(findings),
            risk_level=risk_level,
            findings=findings,
            summary=categories,
        )
    
    async def _run_check(self, rule: ScanRule, config: dict[str, Any]) -> ScanFinding | None:
        """执行自定义检查函数"""
        check_fn = getattr(self, rule.check_fn, None)
        if not check_fn:
            return None
        
        passed, evidence = await check_fn(config)
        if not passed:
            return ScanFinding(
                rule_id=rule.id,
                category=rule.category,
                description=rule.description,
                severity=rule.severity,
                evidence=evidence,
                recommendation=self._get_recommendation(rule),
            )
        return None
    
    async def check_permission_bypass(self, config: dict[str, Any]) -> tuple[bool, str]:
        """检查权限模式"""
        mode = config.get("permission_mode", "default")
        if mode == "bypass":
            return False, f"permission_mode={mode}"
        return True, ""
    
    async def check_tool_count(self, config: dict[str, Any]) -> tuple[bool, str]:
        """检查工具数量"""
        tools = config.get("tools", [])
        if len(tools) > 20:
            return False, f"tools_count={len(tools)}"
        return True, ""
    
    def _calculate_risk(self, findings: list[ScanFinding]) -> RiskLevel:
        """根据发现计算整体风险等级"""
        if not findings:
            return RiskLevel.LOW
        
        severities = [f.severity for f in findings]
        if RiskLevel.CRITICAL in severities:
            return RiskLevel.CRITICAL
        if RiskLevel.HIGH in severities:
            return RiskLevel.HIGH
        if RiskLevel.MEDIUM in severities:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def _get_recommendation(self, rule: ScanRule) -> str:
        """获取修复建议"""
        recommendations = {
            "SHIELD-001": "从系统提示词中移除所有 API Key 和 Token，改用环境变量或凭证系统注入",
            "SHIELD-002": "移除提示词中的密码字段，使用安全的凭证管理方式",
            "SHIELD-003": "绝对不要在提示词中包含私钥内容",
            "SHIELD-004": "限制 Agent 的 Shell 命令权限，使用白名单机制",
            "SHIELD-005": "将权限模式从 bypass 改为 default 或 accept_edits",
            "SHIELD-006": "在系统提示词末尾添加防止注入的指令",
            "SHIELD-007": "移除允许用户修改系统指令的权限",
            "SHIELD-008": "限制 Agent 对外部 URL 的数据发送能力",
            "SHIELD-009": "限制 Agent 对网络文件系统的访问",
            "SHIELD-010": "精简工具数量，移除不必要的工具",
            "SHIELD-011": "限制文件系统写入权限，使用只读模式",
        }
        return recommendations.get(rule.id, "请检查此安全风险并根据业务需求调整配置")
    
    def get_rules(self) -> list[ScanRule]:
        """获取所有扫描规则"""
        return self._rules
    
    def add_rule(self, rule: ScanRule) -> None:
        """添加自定义扫描规则"""
        self._rules.append(rule)


# ── FastAPI 集成 ──────────────────────────────────────────

def create_shield_router():
    """创建 AgentShield 的 FastAPI 路由"""
    from fastapi import APIRouter
    
    router = APIRouter(prefix="/api/shield", tags=["security"])
    shield = AgentShield()
    
    @router.get("/rules")
    async def get_rules():
        """获取所有安全扫描规则"""
        return [
            {
                "id": r.id,
                "category": r.category,
                "description": r.description,
                "severity": r.severity.value,
            }
            for r in shield.get_rules()
        ]
    
    @router.post("/scan")
    async def scan_agent(agent_config: dict[str, Any]):
        """扫描 Agent 配置"""
        result = await shield.scan_agent(agent_config)
        return {
            "agent_name": result.agent_name,
            "risk_level": result.risk_level.value,
            "total_findings": result.total_findings,
            "passed": result.passed,
            "summary": result.summary,
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "category": f.category,
                    "description": f.description,
                    "severity": f.severity.value,
                    "evidence": f.evidence,
                    "recommendation": f.recommendation,
                }
                for f in result.findings
            ],
        }
    
    return router