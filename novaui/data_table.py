"""Dependency-free data table with server-owned filtering and interaction state."""

from __future__ import annotations

import csv
import io
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .components import Component
from .state import State

_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
_WIDTH = re.compile(r"^(?:\d+(?:\.\d+)?(?:px|rem|em|%|vw|ch)|auto)$")


@dataclass(frozen=True)
class ColumnDef:
    """A data field and its presentation options for :class:`DataTable`."""

    key: str
    title: str | None = None
    width: int | str | None = None
    sortable: bool = True
    formatter: Callable[[Any, Mapping[str, Any]], Any] | None = None

    def validate(self) -> None:
        if not isinstance(self.key, str) or not _KEY.fullmatch(self.key):
            raise ValueError("ColumnDef key must be a valid field name of at most 64 characters.")
        if self.title is not None and not isinstance(self.title, str):
            raise TypeError("ColumnDef title must be a string or None.")
        if not isinstance(self.sortable, bool):
            raise TypeError("ColumnDef sortable must be a bool.")
        if self.width is not None:
            if isinstance(self.width, bool) or not isinstance(self.width, (int, str)):
                raise TypeError("ColumnDef width must be a non-negative pixel integer or safe CSS width.")
            if isinstance(self.width, int) and self.width < 0:
                raise ValueError("ColumnDef width must be non-negative.")
            if isinstance(self.width, str) and not _WIDTH.fullmatch(self.width.strip()):
                raise ValueError("ColumnDef width must be a supported CSS width such as '12rem' or '30%'.")
        if self.formatter is not None and not callable(self.formatter):
            raise TypeError("ColumnDef formatter must be callable or None.")

    @property
    def label(self) -> str:
        return self.title if self.title is not None else self.key.replace("_", " ").title()


@dataclass(frozen=True)
class RowAction:
    """A per-row action rendered as a button and called with that row mapping."""

    label: str
    on_click: Callable[[Mapping[str, Any]], Any]

    def validate(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("RowAction label must be a non-empty string.")
        if not callable(self.on_click):
            raise TypeError("RowAction on_click must be callable.")


@dataclass(frozen=True)
class BulkAction:
    """An action applied to the currently selected table rows."""

    label: str
    on_click: Callable[[list[Mapping[str, Any]]], Any]

    def validate(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("BulkAction label must be a non-empty string.")
        if not callable(self.on_click):
            raise TypeError("BulkAction on_click must be callable.")


class _ValueHandler:
    accepts_value = True

    def __init__(self, callback: Callable[[str], Any]):
        self.callback = callback

    def __call__(self, value: str) -> Any:
        if not isinstance(value, str):
            raise TypeError("Table filter values must be strings.")
        return self.callback(value)


class DataTable(Component):
    """Sortable and filterable table for small and medium application datasets.

    The widget maintains transient sort, filter, page, and selection state on its
    component instance. Source rows may be passed directly or through ``State``.
    """

    def __init__(
        self,
        columns: Sequence[ColumnDef],
        data: Sequence[Mapping[str, Any]] | State[list[Mapping[str, Any]]],
        *,
        selectable: bool = False,
        sortable: bool = True,
        searchable: bool = True,
        filterable: bool = True,
        page_size: int = 20,
        row_key: str | None = None,
        loading: bool = False,
        empty_message: str = "No data available.",
        on_row_click: Callable[[Mapping[str, Any]], Any] | None = None,
        on_selection_change: Callable[[list[Mapping[str, Any]]], Any] | None = None,
        row_actions: Sequence[RowAction] = (),
        bulk_actions: Sequence[BulkAction] = (),
        column_visibility: bool = False,
        exportable: bool = False,
        mobile_layout: str = "cards",
        **props: Any,
    ):
        super().__init__(**props)
        self.columns = tuple(columns)
        self.data = data
        self.selectable = selectable
        self.sortable = sortable
        self.searchable = searchable
        self.filterable = filterable
        self.page_size = page_size
        self.row_key = row_key
        self.loading = loading
        self.empty_message = empty_message
        self.on_row_click = on_row_click
        self.on_selection_change = on_selection_change
        self.row_actions = tuple(row_actions)
        self.bulk_actions = tuple(bulk_actions)
        self.column_visibility = column_visibility
        self.exportable = exportable
        self.mobile_layout = mobile_layout
        self._sort_key: str | None = None
        self._sort_descending = False
        self._search = ""
        self._filters: dict[str, str] = {}
        self._page = 0
        self._selected: set[Any] = set()
        self._visible_columns: set[str] = set()
        self._export_requested = False

    def _rows(self) -> list[Mapping[str, Any]]:
        source = self.data.value if isinstance(self.data, State) else self.data
        if not isinstance(source, Sequence) or isinstance(source, (str, bytes, bytearray)):
            raise TypeError("DataTable data must be a sequence of row mappings or State containing one.")
        rows: list[Mapping[str, Any]] = []
        for index, row in enumerate(source):
            if not isinstance(row, Mapping):
                raise TypeError(f"DataTable row {index} must be a mapping.")
            missing = [column.key for column in self.columns if column.key not in row]
            if missing:
                raise ValueError(f"DataTable row {index} is missing column(s): {', '.join(missing)}.")
            rows.append(row)
        return rows

    def _row_identity(self, row: Mapping[str, Any], index: int) -> Any:
        if self.row_key is None:
            return index
        identity = row[self.row_key]
        try:
            hash(identity)
        except TypeError as exc:
            raise TypeError(f"DataTable row key {self.row_key!r} must be hashable.") from exc
        return identity

    @staticmethod
    def _sort_value(value: Any) -> tuple[int, Any]:
        if value is None:
            return (5, "")
        if isinstance(value, bool):
            return (0, int(value))
        if isinstance(value, (int, float)):
            return (1, float(value))
        if isinstance(value, str):
            return (2, value.casefold())
        return (3, str(value).casefold())

    @staticmethod
    def _display(column: ColumnDef, row: Mapping[str, Any]) -> str:
        value = row[column.key]
        result = column.formatter(value, row) if column.formatter is not None else value
        if result is None:
            return ""
        if isinstance(result, (str, int, float, bool)):
            if isinstance(result, float) and not math.isfinite(result):
                raise ValueError(f"Formatter for column {column.key!r} returned a non-finite number.")
            return str(result)
        raise TypeError(f"Formatter for column {column.key!r} must return text or a scalar value.")

    def _validate(self, register_event: Callable[[Callable[..., Any]], str]) -> list[Mapping[str, Any]]:
        if not self.columns:
            raise ValueError("DataTable requires at least one ColumnDef.")
        if any(not isinstance(column, ColumnDef) for column in self.columns):
            raise TypeError("DataTable columns must contain ColumnDef instances.")
        for column in self.columns:
            column.validate()
        keys = [column.key for column in self.columns]
        if len(keys) != len(set(keys)):
            raise ValueError("DataTable column keys must be unique.")
        if self.row_key is not None and (not isinstance(self.row_key, str) or not _KEY.fullmatch(self.row_key)):
            raise ValueError("DataTable row_key must be a valid field name.")
        for name in ("selectable", "sortable", "searchable", "filterable", "loading",
                     "column_visibility", "exportable"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"DataTable {name} must be a bool.")
        if not isinstance(self.mobile_layout, str) or self.mobile_layout not in {"table", "cards"}:
            raise ValueError("DataTable mobile_layout must be 'table' or 'cards'.")
        if isinstance(self.page_size, bool) or not isinstance(self.page_size, int) or not 1 <= self.page_size <= 1000:
            raise ValueError("DataTable page_size must be an integer from 1 to 1000.")
        if not isinstance(self.empty_message, str):
            raise TypeError("DataTable empty_message must be a string.")
        if self.on_row_click is not None and not callable(self.on_row_click):
            raise TypeError("DataTable on_row_click must be callable or None.")
        if self.on_selection_change is not None and not callable(self.on_selection_change):
            raise TypeError("DataTable on_selection_change must be callable or None.")
        if any(not isinstance(action, RowAction) for action in self.row_actions):
            raise TypeError("DataTable row_actions must contain RowAction instances.")
        for action in self.row_actions:
            action.validate()
        if any(not isinstance(action, BulkAction) for action in self.bulk_actions):
            raise TypeError("DataTable bulk_actions must contain BulkAction instances.")
        for action in self.bulk_actions:
            action.validate()
        rows = self._rows()
        if self.row_key is not None:
            missing_keys = [index for index, row in enumerate(rows) if self.row_key not in row]
            if missing_keys:
                raise ValueError(f"DataTable row {missing_keys[0]} is missing row_key {self.row_key!r}.")
        identities = [self._row_identity(row, index) for index, row in enumerate(rows)]
        self._selected.intersection_update(identities)
        valid_columns = set(keys)
        if not self._visible_columns:
            self._visible_columns = valid_columns.copy()
        else:
            self._visible_columns.intersection_update(valid_columns)
            if not self._visible_columns:
                self._visible_columns = valid_columns.copy()
        if self.row_key is not None and len(set(identities)) != len(identities):
            raise ValueError("DataTable row_key values must be unique.")
        return rows

    def _selected_rows(self, rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        return [row for index, row in enumerate(rows) if self._row_identity(row, index) in self._selected]

    def _notify_selection(self, rows: list[Mapping[str, Any]]) -> None:
        if self.on_selection_change is not None:
            self.on_selection_change(self._selected_rows(rows))

    def to_dict(self, register_event: Callable[[Callable[..., Any]], str]) -> dict[str, Any]:
        rows = self._validate(register_event)
        records = list(enumerate(rows))
        if self._sort_key is not None:
            column = next(column for column in self.columns if column.key == self._sort_key)
            if not self.sortable or not column.sortable:
                self._sort_key = None
            else:
                records.sort(key=lambda item: self._sort_value(item[1][self._sort_key]), reverse=self._sort_descending)
        if self._search:
            needle = self._search.casefold()
            records = [
                item for item in records
                if any(needle in str(item[1].get(column.key, "")).casefold() for column in self.columns)
            ]
        for key, value in self._filters.items():
            if value:
                needle = value.casefold()
                records = [item for item in records if needle in str(item[1].get(key, "")).casefold()]

        total = len(records)
        page_count = max(1, math.ceil(total / self.page_size))
        self._page = min(self._page, page_count - 1)
        visible_records = records[self._page * self.page_size : (self._page + 1) * self.page_size]

        def register(callback: Callable[..., Any] | None) -> str | None:
            return register_event(callback) if callback is not None and not self.loading else None

        column_nodes = []
        for column in self.columns:
            if column.key not in self._visible_columns:
                continue
            sort_event_id = None
            if self.sortable and column.sortable:
                def sort_column(key=column.key):
                    if self._sort_key == key:
                        self._sort_descending = not self._sort_descending
                    else:
                        self._sort_key, self._sort_descending = key, False
                    self._page = 0
                sort_event_id = register(sort_column)
            filter_event_id = None
            if self.filterable:
                filter_event_id = register(_ValueHandler(lambda value, key=column.key: self._set_filter(key, value)))
            column_nodes.append({
                "key": column.key,
                "title": column.label,
                "width": f"{column.width}px" if isinstance(column.width, int) else column.width,
                "sort_event_id": sort_event_id,
                "sort_direction": (
                    "desc" if self._sort_descending else "asc"
                ) if self._sort_key == column.key else None,
                "filter_value": self._filters.get(column.key, ""),
                "filter_event_id": filter_event_id,
            })

        search_event_id = register(_ValueHandler(self._set_search)) if self.searchable else None
        visible_ids = {self._row_identity(row, index) for index, row in visible_records}
        all_visible_selected = bool(visible_ids) and visible_ids <= self._selected
        select_all_event_id = None
        if self.selectable:
            def toggle_page_selection():
                if visible_ids <= self._selected and visible_ids:
                    self._selected.difference_update(visible_ids)
                else:
                    self._selected.update(visible_ids)
                self._notify_selection(rows)
            select_all_event_id = register(toggle_page_selection)

        row_nodes = []
        for index, row in visible_records:
            identity = self._row_identity(row, index)
            row_click_event_id = register(lambda current=row: self.on_row_click(current)) if self.on_row_click else None
            action_nodes = [
                {"label": action.label, "event_id": register(lambda current=row, callback=action.on_click: callback(current))}
                for action in self.row_actions
            ]
            row_nodes.append({
                "key": str(identity),
                "cells": [self._display(column, row) for column in self.columns
                          if column.key in self._visible_columns],
                "selected": identity in self._selected,
                "select_event_id": register(
                    lambda current=identity: self._toggle_selection(current, rows)
                ) if self.selectable else None,
                "row_click_event_id": row_click_event_id,
                "actions": action_nodes,
            })

        previous_event_id = register(lambda: self._change_page(-1)) if self._page > 0 else None
        next_event_id = register(lambda: self._change_page(1)) if self._page + 1 < page_count else None
        column_controls = []
        if self.column_visibility:
            for column in self.columns:
                column_controls.append({
                    "key": column.key,
                    "title": column.label,
                    "visible": column.key in self._visible_columns,
                    "event_id": register(lambda key=column.key: self._toggle_column(key))
                    if len(self._visible_columns) > 1 or column.key not in self._visible_columns else None,
                })
        bulk_action_nodes = [
            {"label": action.label, "event_id": register(
                lambda callback=action.on_click: callback(self._selected_rows(rows))
            ) if self._selected else None}
            for action in self.bulk_actions
        ]
        export_csv = self._csv_export(records) if self.exportable and self._export_requested else None
        self._export_requested = False
        return {
            "id": self._node_id(),
            "type": "data_table",
            "columns": column_nodes,
            "rows": row_nodes,
            "selectable": self.selectable,
            "select_all_event_id": select_all_event_id,
            "all_visible_selected": all_visible_selected,
            "selected_count": len(self._selected),
            "searchable": self.searchable,
            "search_value": self._search,
            "search_event_id": search_event_id,
            "sortable": self.sortable,
            "filterable": self.filterable,
            "loading": self.loading,
            "empty_message": self.empty_message,
            "total_rows": total,
            "page": self._page + 1,
            "page_count": page_count,
            "page_size": self.page_size,
            "column_controls": column_controls,
            "bulk_actions": bulk_action_nodes,
            "export_event_id": register(self._request_export) if self.exportable else None,
            "export_csv": export_csv,
            "mobile_layout": self.mobile_layout,
            "previous_event_id": previous_event_id,
            "next_event_id": next_event_id,
            **self._common_props(),
        }

    def _set_search(self, value: str) -> None:
        self._search = value[:256]
        self._page = 0

    def _set_filter(self, key: str, value: str) -> None:
        self._filters[key] = value[:256]
        self._page = 0

    def _change_page(self, offset: int) -> None:
        self._page = max(0, self._page + offset)

    def _toggle_selection(self, identity: Any, rows: list[Mapping[str, Any]]) -> None:
        if identity in self._selected:
            self._selected.remove(identity)
        else:
            self._selected.add(identity)
        self._notify_selection(rows)

    def _toggle_column(self, key: str) -> None:
        if key in self._visible_columns and len(self._visible_columns) > 1:
            self._visible_columns.remove(key)
        else:
            self._visible_columns.add(key)

    def _request_export(self) -> None:
        self._export_requested = True

    def _csv_export(self, records: list[tuple[int, Mapping[str, Any]]]) -> str:
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\r\n")
        columns = [column for column in self.columns if column.key in self._visible_columns]

        def safe_cell(value: str) -> str:
            formula_value = value.lstrip("\ufeff \t\r\n\x00").startswith(("=", "+", "-", "@"))
            return "'" + value if formula_value else value

        writer.writerow([safe_cell(column.label) for column in columns])
        for _, row in records:
            writer.writerow([safe_cell(self._display(column, row)) for column in columns])
        return buffer.getvalue()
