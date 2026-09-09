from __future__ import annotations

import uuid

from bedrock_agent.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    runner = runtime.runner
    session_id = uuid.uuid4().hex
    print("Bedrock Agent v0.3.1（DeepSeek）已启动。输入 /new 开新会话，/skills 查看技能，/quit 退出。")

    while True:
        try:
            text = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return

        if not text:
            continue
        if text == "/quit":
            return
        if text == "/new":
            session_id = uuid.uuid4().hex
            print(f"新会话：{session_id}")
            continue
        if text == "/skills":
            skills = runtime.store.list_skills()
            if not skills:
                print("当前没有已学习技能。")
            for skill in skills:
                print(f"- {skill.name} [{skill.risk}]：{skill.description}")
            continue

        result = runner.run(text, session_id=session_id)
        while result.status == "approval_required":
            pending = result.pending_approval
            assert pending is not None
            print("\n需要本地用户确认：")
            print(f"工具：{pending.tool_call.name}")
            print(f"参数：{pending.tool_call.arguments}")
            print(f"原因：{pending.reason}")
            approved = input("允许执行？[y/N] ").strip().lower() in {"y", "yes"}
            result = runner.resume(pending.approval_id, approved=approved)

        if result.status == "completed":
            print(f"\nAgent> {result.output}")
        else:
            print(f"\n运行失败：{result.error}")
        print(f"trace_id={result.trace_id}")


if __name__ == "__main__":
    main()
