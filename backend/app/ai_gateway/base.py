from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class AIProviderStatus(str, Enum):
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    READY = "ready"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class Citation:
    source_id: str
    title: str
    publisher: str
    license_name: str
    source_url: str
    retrieved_at: str
    section_or_page: str | None = None
    confidence_score: float = 1.0


@dataclass
class GroundedResponse:
    query: str
    grounded_answer: str
    citations: list[Citation]
    retrieved_facts: list[str]
    inference_and_advice: list[str]
    is_refusal: bool = False
    refusal_reason: str | None = None
    model_key: str = "nexora-grounded-eval-v1"
    prompt_version: str = "v1.2.0-safe"
    latency_ms: float = 0.0


# Prompt injection defense patterns
INJECTION_PATTERNS = [
    re.compile(r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b"),
    re.compile(r"(?i)\byou\s+are\s+now\s+(unrestricted|dan|jailbroken|freed)\b"),
    re.compile(r"(?i)\breveal\s+(the\s+)?(system\s+prompt|secret|api[_-]?key|password)\b"),
    re.compile(r"(?i)\bbypass\s+(security|filter|guardrail|rls)\b"),
    re.compile(r"(?i)\bdo\s+anything\s+now\b"),
]


def detect_prompt_injection(user_input: str) -> tuple[bool, str | None]:
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(user_input)
        if match:
            return True, f"Blocked potential prompt injection pattern: '{match.group(0)}'"
    return False, None


@dataclass
class ToolActionPreview:
    action_id: str
    tool_name: str
    target_domain: str
    parameters: dict[str, Any]
    is_write: bool
    requires_human_approval: bool
    approval_token: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ToolRegistry:
    """Least-privilege domain-isolated tool registry."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        domain: str,
        is_write: bool,
        description: str,
        handler: Callable[..., Any],
        requires_approval: bool = False,
    ) -> None:
        self._tools[name] = {
            "name": name,
            "domain": domain,
            "is_write": is_write,
            "description": description,
            "handler": handler,
            "requires_approval": requires_approval or is_write,
        }

    def get_tool(self, name: str) -> dict[str, Any] | None:
        return self._tools.get(name)

    def list_tools(self, domain: str | None = None) -> list[dict[str, Any]]:
        tools = list(self._tools.values())
        if domain:
            tools = [t for t in tools if t["domain"] == domain or t["domain"] == "shared"]
        return [{k: v for k, v in t.items() if k != "handler"} for t in tools]

    def create_action_preview(self, tool_name: str, parameters: dict[str, Any]) -> ToolActionPreview:
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} is not registered in allowlist")
        is_write = tool["is_write"]
        requires_approval = tool["requires_approval"]
        approval_token = str(uuid4()) if requires_approval else None
        return ToolActionPreview(
            action_id=str(uuid4()),
            tool_name=tool_name,
            target_domain=tool["domain"],
            parameters=parameters,
            is_write=is_write,
            requires_human_approval=requires_approval,
            approval_token=approval_token,
        )


tool_registry = ToolRegistry()
