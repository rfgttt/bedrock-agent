from __future__ import annotations

import hmac
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from bedrock_agent.bootstrap import Runtime, build_runtime
from bedrock_agent.security import LocalTokenStore, is_loopback, require_loopback_bind


class RunRequest(BaseModel):
    input: str = Field(min_length=1, max_length=20_000)
    session_id: str | None = Field(default=None, max_length=128)


class ApprovalRequest(BaseModel):
    approved: bool


class LocalAccess:
    def __init__(self, token: str) -> None:
        self.token = token

    async def __call__(
        self,
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        # Intentionally ignore X-Forwarded-For. Bedrock is not designed to sit
        # behind a remote proxy; the socket peer must itself be loopback.
        client_host = request.client.host if request.client else None
        if not is_loopback(client_host):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Local access only")
        expected = f"Bearer {self.token}"
        if not authorization or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid local token")


def _result_payload(result) -> dict:
    payload = {
        "status": result.status,
        "session_id": result.session_id,
        "trace_id": result.trace_id,
        "output": result.output,
        "error": result.error,
    }
    if result.pending_approval:
        payload["pending_approval"] = {
            "approval_id": result.pending_approval.approval_id,
            "tool": result.pending_approval.tool_call.name,
            "arguments": result.pending_approval.tool_call.arguments,
            "reason": result.pending_approval.reason,
        }
    return payload


def create_app(runtime: Runtime, token: str) -> FastAPI:
    app = FastAPI(title="Bedrock Local API", version="0.3.1")
    local_access = LocalAccess(token)

    @app.get("/v1/health", dependencies=[Depends(local_access)])
    def health() -> dict:
        return {
            "ok": True,
            "scope": "loopback-only",
            "owner_user": runtime.settings.owner_user,
            "tools": runtime.registry.names(),
        }

    @app.post("/v1/run", dependencies=[Depends(local_access)])
    def run(request: RunRequest) -> dict:
        return _result_payload(runtime.runner.run(request.input, session_id=request.session_id))

    @app.post("/v1/approvals/{approval_id}", dependencies=[Depends(local_access)])
    def approve(approval_id: str, request: ApprovalRequest) -> dict:
        try:
            result = runtime.runner.resume(approval_id, approved=request.approved)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _result_payload(result)

    @app.get("/v1/memories", dependencies=[Depends(local_access)])
    def memories(query: str = "", limit: int = 20) -> list[dict]:
        records = (
            runtime.store.search_memories(query, limit=limit)
            if query
            else runtime.store.list_memories(limit=limit)
        )
        return [
            {
                "memory_id": record.memory_id,
                "kind": record.kind,
                "content": record.content,
                "tags": record.tags,
                "importance": record.importance,
                "created_at": record.created_at,
                "score": record.score,
            }
            for record in records
        ]

    @app.get("/v1/skills", dependencies=[Depends(local_access)])
    def skills() -> list[dict]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "risk": skill.risk,
                "steps": skill.steps,
            }
            for skill in runtime.store.list_skills()
        ]

    return app


def main() -> None:
    runtime = build_runtime()
    settings = runtime.settings
    require_loopback_bind(settings.bind_host)
    token = LocalTokenStore(settings.token_file).get_or_create()
    print(f"Bedrock Local API: http://{settings.bind_host}:{settings.bind_port}")
    print(f"本地令牌文件：{settings.token_file.resolve()}")
    uvicorn.run(
        create_app(runtime, token),
        host=settings.bind_host,
        port=settings.bind_port,
        proxy_headers=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
