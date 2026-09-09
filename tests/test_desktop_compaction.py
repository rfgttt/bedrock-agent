from bedrock_agent.desktop import BedrockDesktop


def test_study_plan_tool_arguments_are_compacted_for_chat() -> None:
    text = BedrockDesktop._compact_tool_arguments(
        "create_study_plan",
        {
            "title": "30天计划",
            "goal": "学习",
            "days": 30,
            "daily_minutes": 90,
            "topics": [f"Day {index}" for index in range(30)],
        },
    )

    assert "topics_count" in text
    assert "Day 29" not in text
    assert len(text) < 500
