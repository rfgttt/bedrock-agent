from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from bedrock_agent.tools.base import RiskLevel, Tool


class Decision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    decision: Decision
    reason: str


class DefaultToolPolicy:
    """Safe-by-default policy.

    Read-only tools execute automatically, writes and external effects require
    approval, and dangerous tools are denied unless the policy is explicitly
    replaced by the application.
    """

    def evaluate(self, tool: Tool, arguments: dict[str, Any]) -> PolicyDecision:
        del arguments
        if tool.risk is RiskLevel.READ_ONLY:
            return PolicyDecision(Decision.ALLOW, "Read-only tool")
        if tool.risk in {RiskLevel.WRITE, RiskLevel.EXTERNAL}:
            return PolicyDecision(Decision.REQUIRE_APPROVAL, f"Tool risk is {tool.risk.value}")
        return PolicyDecision(Decision.DENY, "Dangerous tools are disabled by default")
