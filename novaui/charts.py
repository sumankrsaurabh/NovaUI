"""Small dependency-free chart components rendered with accessible SVG."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .components import Component

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_CHART_KINDS = {"line", "bar", "area", "doughnut"}


@dataclass(frozen=True)
class ChartDataset:
    """One named chart series. Values correspond to the chart's labels."""

    label: str
    values: Sequence[int | float]
    color: str | None = None


class Chart(Component):
    """Responsive line, bar, area, or doughnut chart using browser-native SVG.

    Example::

        ui.Chart(
            ["Jan", "Feb", "Mar"],
            [ui.ChartDataset("Revenue", [18, 26, 22])],
            kind="line",
            title="Quarterly revenue",
        )
    """

    def __init__(
        self,
        labels: Sequence[str],
        datasets: Sequence[ChartDataset] | Mapping[str, Sequence[int | float]],
        *,
        kind: str = "line",
        title: str = "",
        width: int | None = None,
        height: int = 280,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.labels = labels
        self.datasets = (
            [ChartDataset(name, values) for name, values in datasets.items()]
            if isinstance(datasets, Mapping)
            else datasets
        )
        self.kind = kind
        self.title = title
        self.width = width
        self.height = height

    def to_dict(self, register_event):
        if not isinstance(self.labels, Sequence) or isinstance(self.labels, (str, bytes)):
            raise TypeError("Chart labels must be a sequence of strings.")
        if len(self.labels) > 500:
            raise ValueError("Chart supports at most 500 labels per series.")
        if any(not isinstance(label, str) for label in self.labels):
            raise TypeError("Every chart label must be a string.")
        if not isinstance(self.kind, str) or self.kind not in _CHART_KINDS:
            raise ValueError(f"Chart kind must be one of: {', '.join(sorted(_CHART_KINDS))}.")
        if not isinstance(self.title, str):
            raise TypeError("Chart title must be a string.")
        if isinstance(self.height, bool) or not isinstance(self.height, int) or not 120 <= self.height <= 900:
            raise ValueError("Chart height must be an integer from 120 to 900 pixels.")
        if not isinstance(self.datasets, Sequence) or isinstance(self.datasets, (str, bytes)):
            raise TypeError("Chart datasets must be a sequence of ChartDataset values or a mapping.")
        if len(self.datasets) > 8:
            raise ValueError("Chart supports at most 8 datasets.")

        datasets = []
        for dataset in self.datasets:
            if not isinstance(dataset, ChartDataset):
                raise TypeError("Each chart dataset must be a ChartDataset.")
            if not isinstance(dataset.label, str) or not dataset.label.strip():
                raise ValueError("Chart dataset labels must be non-empty strings.")
            if not isinstance(dataset.values, Sequence) or isinstance(dataset.values, (str, bytes)):
                raise TypeError("Chart dataset values must be a sequence of numbers.")
            if len(dataset.values) != len(self.labels):
                raise ValueError("Every chart dataset must have one value for each chart label.")
            values = []
            for value in dataset.values:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError("Chart values must be finite numbers.")
                try:
                    finite = math.isfinite(value)
                except OverflowError:
                    finite = False
                if not finite:
                    raise ValueError("Chart values must be finite numbers.")
                if abs(value) > 1e100:
                    raise ValueError("Chart values must have an absolute value no greater than 1e100.")
                if self.kind == "doughnut" and value < 0:
                    raise ValueError("Doughnut chart values must be non-negative.")
                values.append(value)
            if dataset.color is not None and (
                not isinstance(dataset.color, str) or not _HEX_COLOR.fullmatch(dataset.color)
            ):
                raise ValueError("Chart dataset color must be a six-digit hex color such as '#4F46E5'.")
            if self.kind == "doughnut" and dataset.color is not None:
                raise ValueError("Doughnut slice colors use NovaUI's built-in palette; omit dataset color.")
            datasets.append({"label": dataset.label, "values": values, "color": dataset.color})

        if self.kind == "doughnut" and len(datasets) > 1:
            raise ValueError("Doughnut charts accept one dataset; use labels for the slices.")
        width = self.width
        if width is not None and (isinstance(width, bool) or not isinstance(width, int) or width < 1):
            raise ValueError("Chart width must be a positive pixel integer or omitted.")
        return {
            "id": self._node_id(), "type": "chart", "kind": self.kind, "title": self.title,
            "height": self.height, "width": width, "labels": list(self.labels), "datasets": datasets,
            **self._common_props(),
        }
