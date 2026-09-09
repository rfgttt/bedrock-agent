from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QByteArray, Property, Signal, Slot


class StableListModel(QAbstractListModel):
    countChanged = Signal()
    """A small immutable-row list model with change suppression.

    The model only emits a reset when the semantic payload changed. Chat-like
    feeds can append rows without rebuilding existing delegates.
    """

    def __init__(self, roles: Iterable[str], parent=None) -> None:
        super().__init__(parent)
        self._roles = tuple(dict.fromkeys(roles))
        self._role_ids = {Qt.UserRole + index + 1: role for index, role in enumerate(self._roles)}
        self._role_lookup = {role: role_id for role_id, role in self._role_ids.items()}
        self._rows: list[dict[str, Any]] = []
        self._fingerprint = self._digest([])

    @staticmethod
    def _digest(rows: list[dict[str, Any]]) -> str:
        payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802 - Qt API
        return {role_id: QByteArray(name.encode("utf-8")) for role_id, name in self._role_ids.items()}

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802 - Qt API
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        key = self._role_ids.get(role)
        if key is None:
            return None
        return self._rows[index.row()].get(key)

    def rows(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._rows]

    def set_rows(self, rows: Iterable[Mapping[str, Any]], *, force: bool = False) -> bool:
        normalized = [{role: row.get(role) for role in self._roles} for row in rows]
        fingerprint = self._digest(normalized)
        if not force and fingerprint == self._fingerprint:
            return False
        self.beginResetModel()
        self._rows = normalized
        self._fingerprint = fingerprint
        self.endResetModel()
        self.countChanged.emit()
        return True

    def append_rows(self, rows: Iterable[Mapping[str, Any]]) -> int:
        normalized = [{role: row.get(role) for role in self._roles} for row in rows]
        if not normalized:
            return 0
        start = len(self._rows)
        self.beginInsertRows(QModelIndex(), start, start + len(normalized) - 1)
        self._rows.extend(normalized)
        self.endInsertRows()
        self.countChanged.emit()
        self._fingerprint = self._digest(self._rows)
        return len(normalized)

    def clear(self) -> None:
        self.set_rows([], force=True)

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, Any] | None:
        if not 0 <= row < len(self._rows):
            return None
        return dict(self._rows[row])

    def replace_or_append(self, key: str, value: Any, row: Mapping[str, Any]) -> None:
        normalized = {role: row.get(role) for role in self._roles}
        for index, existing in enumerate(self._rows):
            if existing.get(key) == value:
                if existing == normalized:
                    return
                self._rows[index] = normalized
                model_index = self.index(index, 0)
                self.dataChanged.emit(model_index, model_index, list(self._role_ids))
                self._fingerprint = self._digest(self._rows)
                return
        self.append_rows([normalized])
