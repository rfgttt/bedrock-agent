import pytest
pytest.importorskip("PySide6")

from bedrock_agent.desktop_qml.models import StableListModel


def test_stable_model_skips_unchanged_reset_and_appends_incrementally() -> None:
    model = StableListModel(("id", "name"))
    assert model.set_rows([{"id": "1", "name": "A"}]) is True
    assert model.set_rows([{"id": "1", "name": "A"}]) is False
    assert model.count == 1
    assert model.append_rows([{"id": "2", "name": "B"}]) == 1
    assert model.count == 2
    assert model.get(1) == {"id": "2", "name": "B"}
