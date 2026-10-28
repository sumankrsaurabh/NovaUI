"""Windowed rendering for large plain-text lists."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any

from .components import Component


class _ScrollBinding:
    accepts_value = True

    def __init__(self, owner: VirtualList):
        self.owner = owner

    def __call__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("VirtualList scroll position must be numeric text.")
        try:
            position = float(value)
        except ValueError as exc:
            raise ValueError("VirtualList scroll position must be finite.") from exc
        if not math.isfinite(position) or position < 0:
            raise ValueError("VirtualList scroll position must be finite and non-negative.")
        self.owner._scroll_top = min(position, self.owner.total_height)


class VirtualList(Component):
    """Render a bounded visible window from a sequence of text items."""

    def __init__(
        self,
        items: Sequence[str],
        *,
        item_height: int = 40,
        height: int = 320,
        overscan: int = 3,
        label: str = "List",
        **props: Any,
    ):
        super().__init__(**props)
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            raise TypeError("VirtualList items must be a sequence of strings.")
        if any(not isinstance(item, str) for item in items):
            raise TypeError("VirtualList items must contain only strings.")
        for name, value in (("item_height", item_height), ("height", height)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"VirtualList {name} must be a positive integer.")
        if isinstance(overscan, bool) or not isinstance(overscan, int) or not 0 <= overscan <= 40:
            raise ValueError("VirtualList overscan must be an integer from 0 to 40.")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("VirtualList label must be a non-empty accessible name.")
        self.items = items
        self.item_height = item_height
        self.height = height
        self.overscan = overscan
        self.label = label.strip()
        self._scroll_top = 0.0
        self._scroll_action = _ScrollBinding(self)

    @property
    def total_height(self) -> int:
        return len(self.items) * self.item_height

    def to_dict(self, register_event: Callable[[Callable[..., object]], str]) -> dict[str, object]:
        if not isinstance(self.items, Sequence) or isinstance(self.items, (str, bytes)):
            raise TypeError("VirtualList items must be a sequence of strings.")
        if any(not isinstance(item, str) for item in self.items):
            raise TypeError("VirtualList items must contain only strings.")
        visible_count = math.ceil(self.height / self.item_height) + self.overscan * 2
        start = max(0, int(self._scroll_top // self.item_height) - self.overscan)
        end = min(len(self.items), start + visible_count)
        return {
            "id": self._node_id(),
            "type": "virtual_list",
            "label": self.label,
            "height": self.height,
            "item_height": self.item_height,
            "total": len(self.items),
            "start": start,
            "top_padding": start * self.item_height,
            "bottom_padding": (len(self.items) - end) * self.item_height,
            "items": [
                {"key": str(index), "text": self.items[index], "index": index}
                for index in range(start, end)
            ],
            "scroll_event_id": (
                register_event(self._scroll_action) if len(self.items) > visible_count else None
            ),
            **self._common_props(),
        }
