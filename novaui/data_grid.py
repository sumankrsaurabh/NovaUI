"""Editable, keyboard-navigable data grid."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .components import Component
from .data_table import ColumnDef, DataTable
from .state import State


class _CellValueHandler:
    accepts_value = True

    def __init__(self, callback: Callable[[str], Any]):
        self.callback = callback

    def __call__(self, value: str) -> Any:
        if not isinstance(value, str):
            raise TypeError("DataGrid cell values must be strings.")
        return self.callback(value)


class _GridPasteHandler:
    accepts_value = True

    def __init__(self, grid: DataGrid, row: int, column: int):
        self.grid = grid
        self.row = row
        self.column = column

    def __call__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("DataGrid paste contents must be text.")
        try:
            payload_size = len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("DataGrid paste contents must be valid Unicode text.") from exc
        if payload_size + 128 > 16_384:
            raise ValueError("DataGrid paste contents exceed the 16 KiB limit.")
        self.grid._paste(self.row, self.column, value)


class DataGrid(Component):
    """A small editable grid with keyboard navigation and bounded undo/redo."""

    def __init__(
        self,
        columns: Sequence[ColumnDef],
        data: Sequence[Mapping[str, Any]] | State[list[Mapping[str, Any]]],
        *,
        editable: bool = True,
        editable_columns: Sequence[str] | None = None,
        on_change: Callable[[list[dict[str, Any]]], Any] | None = None,
        **props: Any,
    ):
        super().__init__(**props)
        self.columns = tuple(columns)
        self.data = data
        self.editable = editable
        self.editable_columns = None if editable_columns is None else frozenset(editable_columns)
        self.on_change = on_change
        self._local_rows: list[dict[str, Any]] | None = None
        self._undo: list[tuple[int, str, Any, Any]] = []
        self._redo: list[tuple[int, str, Any, Any]] = []

    def _rows(self) -> list[dict[str, Any]]:
        source = self._local_rows
        if source is None:
            source = self.data.value if isinstance(self.data, State) else self.data
        if not isinstance(source, Sequence) or isinstance(source, (str, bytes, bytearray)):
            raise TypeError("DataGrid data must be a sequence of row mappings or State containing one.")
        rows: list[dict[str, Any]] = []
        keys = [column.key for column in self.columns]
        for index, row in enumerate(source):
            if not isinstance(row, Mapping):
                raise TypeError(f"DataGrid row {index} must be a mapping.")
            if any(key not in row for key in keys):
                raise ValueError(f"DataGrid row {index} is missing one or more declared columns.")
            rows.append(dict(row))
        return rows

    def _validate(self) -> list[dict[str, Any]]:
        if not self.columns or any(not isinstance(column, ColumnDef) for column in self.columns):
            raise ValueError("DataGrid requires at least one ColumnDef.")
        for column in self.columns:
            column.validate()
        keys = [column.key for column in self.columns]
        if len(keys) != len(set(keys)):
            raise ValueError("DataGrid column keys must be unique.")
        if not isinstance(self.editable, bool):
            raise TypeError("DataGrid editable must be a bool.")
        if self.editable_columns is not None and not self.editable_columns <= set(keys):
            raise ValueError("DataGrid editable_columns must contain declared column keys.")
        if self.on_change is not None and not callable(self.on_change):
            raise TypeError("DataGrid on_change must be callable or None.")
        rows = self._rows()
        editable_columns = (
            self.editable_columns
            if self.editable_columns is not None
            else frozenset(keys)
        )
        if self.editable and any(
            column.formatter is not None and column.key in editable_columns
            for column in self.columns
        ):
            raise ValueError("Editable DataGrid columns cannot use formatters because formatted values are not reversible.")
        for row in rows:
            for column in self.columns:
                DataTable._display(column, row)
        return rows

    def to_dict(self, register_event: Callable[[Callable[..., Any]], str]) -> dict[str, Any]:
        rows = self._validate()
        editable_columns = (
            self.editable_columns
            if self.editable_columns is not None
            else frozenset(column.key for column in self.columns)
        )
        columns = [{"key": column.key, "title": column.label} for column in self.columns]
        row_nodes = []
        for row_index, row in enumerate(rows):
            cells = []
            for column_index, column in enumerate(self.columns):
                editable = self.editable and column.key in editable_columns
                event_id = None
                if editable:
                    event_id = register_event(_CellValueHandler(
                        lambda value, index=row_index, key=column.key: self._edit(index, key, value)
                    ))
                cells.append({
                    "value": DataTable._display(column, row),
                    "editable": editable,
                    "event_id": event_id,
                    "paste_event_id": (
                        register_event(_GridPasteHandler(self, row_index, column_index))
                        if editable else None
                    ),
                })
            row_nodes.append({"key": str(row_index), "cells": cells})
        return {
            "id": self._node_id(),
            "type": "data_grid",
            "columns": columns,
            "rows": row_nodes,
            "undo_event_id": register_event(self._undo_edit) if self._undo else None,
            "redo_event_id": register_event(self._redo_edit) if self._redo else None,
            **self._common_props(),
        }

    def _write(self, rows: list[dict[str, Any]]) -> None:
        if isinstance(self.data, State):
            self.data.value = rows
        else:
            self._local_rows = rows

    def _notify_change(self, rows: list[dict[str, Any]]) -> None:
        if self.on_change is not None:
            self.on_change([dict(row) for row in rows])

    def _edit(self, row_index: int, key: str, value: str) -> None:
        rows = self._rows()
        old_value = rows[row_index][key]
        if value == str(old_value):
            return
        rows[row_index][key] = value
        self._undo.append((row_index, key, old_value, value))
        del self._undo[:-100]
        self._redo.clear()
        self._write(rows)
        self._notify_change(rows)

    def _paste(self, start_row: int, start_column: int, text: str) -> None:
        if not text:
            return
        try:
            matrix = list(csv.reader(io.StringIO(text), delimiter="\t", strict=True))
        except csv.Error as exc:
            raise ValueError("DataGrid paste contents are not valid tab-separated text.") from exc
        if text.endswith(("\n", "\r")) and matrix and matrix[-1] == []:
            matrix.pop()
        if not matrix or not matrix[0] or any(len(row) != len(matrix[0]) for row in matrix):
            raise ValueError("DataGrid paste contents must form a non-empty rectangular range.")

        rows = self._rows()
        editable_columns = (
            self.editable_columns
            if self.editable_columns is not None
            else frozenset(column.key for column in self.columns)
        )
        if start_row + len(matrix) > len(rows) or start_column + len(matrix[0]) > len(self.columns):
            raise ValueError("DataGrid paste range extends beyond the existing grid.")

        edits = []
        for row_offset, values in enumerate(matrix):
            for column_offset, value in enumerate(values):
                row_index = start_row + row_offset
                column = self.columns[start_column + column_offset]
                if not self.editable or column.key not in editable_columns:
                    raise ValueError("DataGrid paste range includes a non-editable cell.")
                old_value = rows[row_index][column.key]
                if value != str(old_value):
                    edits.append((row_index, column.key, old_value, value))
                    rows[row_index][column.key] = value
        if not edits:
            return
        self._undo.extend(edits)
        del self._undo[:-100]
        self._redo.clear()
        self._write(rows)
        self._notify_change(rows)

    def _undo_edit(self) -> None:
        if not self._undo:
            return
        row_index, key, old_value, new_value = self._undo[-1]
        rows = self._rows()
        if row_index >= len(rows) or key not in rows[row_index] or rows[row_index][key] != new_value:
            self._undo.clear()
            self._redo.clear()
            raise ValueError("DataGrid history was cleared because the underlying data changed.")
        rows[row_index][key] = old_value
        self._undo.pop()
        self._redo.append((row_index, key, old_value, new_value))
        self._write(rows)
        self._notify_change(rows)

    def _redo_edit(self) -> None:
        if not self._redo:
            return
        row_index, key, old_value, new_value = self._redo[-1]
        rows = self._rows()
        if row_index >= len(rows) or key not in rows[row_index] or rows[row_index][key] != old_value:
            self._undo.clear()
            self._redo.clear()
            raise ValueError("DataGrid history was cleared because the underlying data changed.")
        rows[row_index][key] = new_value
        self._redo.pop()
        self._undo.append((row_index, key, old_value, new_value))
        self._write(rows)
        self._notify_change(rows)
