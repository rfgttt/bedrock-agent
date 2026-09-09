from __future__ import annotations

from dataclasses import dataclass

from bedrock_agent.agent import AgentRunner
from bedrock_agent.capabilities import CapabilitySuite, build_capability_suite
from bedrock_agent.config import Settings
from bedrock_agent.integrations import MCPManager, MCPServerCatalog
from bedrock_agent.learning import (
    MemoryService,
    SkillManager,
    build_memory_tools,
    build_skill_learning_tool,
)
from bedrock_agent.security import make_private_dir, require_owner_user
from bedrock_agent.store import SQLiteStore
from bedrock_agent.tools import ToolRegistry, build_default_tools
from bedrock_agent.tracing import TraceWriter


@dataclass(slots=True)
class Runtime:
    settings: Settings
    runner: AgentRunner
    store: SQLiteStore
    registry: ToolRegistry
    memory: MemoryService
    skills: SkillManager
    capabilities: CapabilitySuite
    mcp: MCPManager

    def close(self) -> None:
        for resource in (self.runner.model, self.capabilities.web):
            close = getattr(resource, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    # Shutdown/reconfiguration cleanup must not leave the UI stuck.
                    continue


def build_runtime(settings: Settings | None = None, *, model=None) -> Runtime:
    settings = settings or Settings.from_env()
    require_owner_user(settings.owner_user)
    make_private_dir(settings.data_dir)
    make_private_dir(settings.trace_dir)
    make_private_dir(settings.workspace)

    store = SQLiteStore(settings.db_path)
    registry = ToolRegistry(build_default_tools(settings.workspace))
    memory = MemoryService(
        store,
        context_limit=settings.memory_context_limit,
        episode_limit=settings.episode_memory_limit,
    )
    for tool in build_memory_tools(memory):
        registry.register(tool)

    capabilities, capability_tools = build_capability_suite(
        workspace_path=settings.workspace,
        data_dir=settings.data_dir,
    )
    for tool in capability_tools:
        registry.register(tool)

    mcp = MCPManager(MCPServerCatalog(settings.data_dir / "mcp_servers.json"), registry)
    # MCP synchronization is intentionally user-triggered from the desktop UI.
    # Starting an enabled stdio server during bootstrap could block the first
    # window, so no external process or network connection is opened here.

    skills = SkillManager(store, registry)
    registry.register(build_skill_learning_tool(skills))
    skills.load_active()

    if model is None:
        from bedrock_agent.llm.openai_compatible import OpenAICompatibleModel

        model = OpenAICompatibleModel(
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=settings.model,
            timeout_seconds=settings.model_timeout_seconds,
            max_retries=settings.model_max_retries,
        )

    runner = AgentRunner(
        model=model,
        tools=registry,
        store=store,
        tracer=TraceWriter(settings.trace_dir, file_limit=settings.trace_file_limit),
        memory=memory,
        max_steps=settings.max_steps,
        message_limit=settings.model_message_limit,
    )
    return Runtime(settings, runner, store, registry, memory, skills, capabilities, mcp)
