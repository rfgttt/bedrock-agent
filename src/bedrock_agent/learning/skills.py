from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict
from typing import Any

from bedrock_agent.domain import SkillDefinition
from bedrock_agent.store import SQLiteStore
from bedrock_agent.tools.base import RiskLevel, Tool
from bedrock_agent.tools.registry import ToolRegistry


_SKILL_NAME = re.compile(r"^[a-z][a-z0-9_]{2,48}$")
_FIELD_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,48}$")
_FULL_PLACEHOLDER = re.compile(r"^\{\{([^{}]+)}}$")
_PLACEHOLDER = re.compile(r"\{\{([^{}]+)}}")
_RISK_ORDER = {
    RiskLevel.READ_ONLY: 0,
    RiskLevel.WRITE: 1,
    RiskLevel.EXTERNAL: 2,
    RiskLevel.DANGEROUS: 3,
}
_FORBIDDEN_CHILDREN = {"propose_recipe_skill", "remember_lesson"}
_ALLOWED_PARAMETER_TYPES = {"string", "integer", "number", "boolean"}


class SkillManager:
    """Installs constrained recipe skills composed only from existing tools.

    This is deliberate: Bedrock can learn new reusable behavior without being
    allowed to write or import arbitrary Python into its own process.
    """

    def __init__(self, store: SQLiteStore, registry: ToolRegistry) -> None:
        self.store = store
        self.registry = registry

    def load_active(self) -> None:
        for definition in self.store.list_skills():
            self.registry.register(self._to_tool(definition))

    def install_from_proposal(self, proposal: dict[str, Any]) -> dict[str, Any]:
        definition = self._validate_and_build(proposal)
        self.store.save_skill(definition)
        self.registry.register(self._to_tool(definition))
        return {
            "installed": True,
            "skill": asdict(definition),
            "note": "Recipe skills can call only pre-registered tools; arbitrary Python was not installed.",
        }

    def _validate_and_build(self, proposal: dict[str, Any]) -> SkillDefinition:
        name = str(proposal.get("name", "")).strip()
        description = str(proposal.get("description", "")).strip()
        parameters = proposal.get("parameters")
        steps = proposal.get("steps")

        if not _SKILL_NAME.fullmatch(name):
            raise ValueError("Skill name must be snake_case, 3-49 characters")
        if self.registry.contains(name):
            raise ValueError(f"A tool or skill named {name!r} already exists")
        if not description or len(description) > 500:
            raise ValueError("Skill description must be 1-500 characters")
        self._validate_parameter_schema(parameters)
        if not isinstance(steps, list) or not 1 <= len(steps) <= 8:
            raise ValueError("A recipe skill must contain 1-8 steps")

        highest_risk = RiskLevel.READ_ONLY
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or set(step) != {"tool", "arguments"}:
                raise ValueError(f"Step {index} must contain exactly tool and arguments")
            tool_name = step["tool"]
            if not isinstance(tool_name, str) or tool_name in _FORBIDDEN_CHILDREN:
                raise ValueError(f"Step {index} uses a forbidden meta-tool")
            tool = self.registry.get(tool_name)
            if tool.risk is RiskLevel.DANGEROUS:
                raise ValueError("Dangerous tools cannot be installed inside learned skills")
            if _RISK_ORDER[tool.risk] > _RISK_ORDER[highest_risk]:
                highest_risk = tool.risk
            if not isinstance(step["arguments"], dict):
                raise ValueError(f"Step {index} arguments must be an object")
            self._validate_templates(step["arguments"], parameters, current_step=index)

        return SkillDefinition(
            skill_id=uuid.uuid4().hex,
            name=name,
            description=description,
            parameters=parameters,
            steps=steps,
            risk=highest_risk.value,
        )

    @staticmethod
    def _validate_parameter_schema(schema: Any) -> None:
        if not isinstance(schema, dict) or schema.get("type") != "object":
            raise ValueError("Skill parameters must be a JSON schema object")
        properties = schema.get("properties", {})
        if not isinstance(properties, dict) or len(properties) > 12:
            raise ValueError("Skill parameters.properties must contain at most 12 fields")
        if schema.get("additionalProperties", False) is not False:
            raise ValueError("Skill schema must set additionalProperties to false")
        for field, definition in properties.items():
            if not _FIELD_NAME.fullmatch(field):
                raise ValueError(f"Invalid parameter name: {field}")
            if not isinstance(definition, dict) or definition.get("type") not in _ALLOWED_PARAMETER_TYPES:
                raise ValueError(f"Parameter {field} must use a primitive JSON type")
        required = schema.get("required", [])
        if not isinstance(required, list) or not set(required).issubset(properties):
            raise ValueError("Skill required fields must exist in properties")

    def _validate_templates(self, value: Any, parameters: dict[str, Any], *, current_step: int) -> None:
        if isinstance(value, dict):
            for item in value.values():
                self._validate_templates(item, parameters, current_step=current_step)
            return
        if isinstance(value, list):
            for item in value:
                self._validate_templates(item, parameters, current_step=current_step)
            return
        if not isinstance(value, str):
            return
        for expression in _PLACEHOLDER.findall(value):
            parts = expression.split(".")
            if len(parts) == 2 and parts[0] == "input":
                if parts[1] not in parameters.get("properties", {}):
                    raise ValueError(f"Unknown input placeholder: {expression}")
                continue
            if len(parts) >= 3 and parts[0] == "steps" and parts[1].isdigit():
                if int(parts[1]) >= current_step:
                    raise ValueError("A step can reference only earlier step results")
                continue
            raise ValueError(f"Unsupported placeholder: {expression}")

    def _to_tool(self, definition: SkillDefinition) -> Tool:
        risk = RiskLevel(definition.risk)

        def execute(arguments: dict[str, Any]) -> dict[str, Any]:
            step_results: list[dict[str, Any]] = []
            for index, step in enumerate(definition.steps):
                child = self.registry.get(step["tool"])
                rendered = self._render(step["arguments"], arguments, step_results)
                self.registry.validate_arguments(child, rendered)
                result = child.handler(rendered)
                step_results.append({"tool": child.name, "result": result})
            return {"skill": definition.name, "steps": step_results}

        return Tool(
            name=definition.name,
            description=f"Learned recipe skill: {definition.description}",
            parameters=definition.parameters,
            handler=execute,
            risk=risk,
        )

    def _render(self, value: Any, inputs: dict[str, Any], steps: list[dict[str, Any]]) -> Any:
        if isinstance(value, dict):
            return {key: self._render(item, inputs, steps) for key, item in value.items()}
        if isinstance(value, list):
            return [self._render(item, inputs, steps) for item in value]
        if not isinstance(value, str):
            return value

        full = _FULL_PLACEHOLDER.fullmatch(value)
        if full:
            return self._lookup(full.group(1), inputs, steps)

        return _PLACEHOLDER.sub(
            lambda match: str(self._lookup(match.group(1), inputs, steps)),
            value,
        )

    @staticmethod
    def _lookup(expression: str, inputs: dict[str, Any], steps: list[dict[str, Any]]) -> Any:
        parts = expression.split(".")
        if parts[0] == "input":
            return inputs[parts[1]]
        current: Any = steps[int(parts[1])]
        for part in parts[2:]:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                raise KeyError(f"Cannot resolve placeholder {expression}")
        return current


def build_skill_learning_tool(manager: SkillManager) -> Tool:
    def propose(arguments: dict[str, Any]) -> dict[str, Any]:
        return manager.install_from_proposal(arguments)

    return Tool(
        name="propose_recipe_skill",
        description=(
            "Propose a reusable skill made only by composing existing tools. Installation requires the "
            "local user's approval. This cannot install arbitrary Python, shell commands, or new dependencies."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "parameters": {"type": "object"},
                "steps": {"type": "array"},
            },
            "required": ["name", "description", "parameters", "steps"],
            "additionalProperties": False,
        },
        handler=propose,
        risk=RiskLevel.WRITE,
    )
