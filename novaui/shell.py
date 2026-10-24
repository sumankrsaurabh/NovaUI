"""Small application-shell compositions built from existing layout components."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .components import Column, Component, Row, Text
from .routing import navigate
from .state import State, state


def AppShell(*children: Component, **props: Any) -> Row:
    props.setdefault("min_height", "100vh")
    props.setdefault("class_name", "nova-app-shell")
    return Row(*children, align="stretch", **props)


def Header(*children: Component, **props: Any) -> Row:
    props.setdefault("padding", 12)
    props.setdefault("class_name", "nova-header")
    return Row(*children, align="center", **props)


def Sidebar(*children: Component, collapsed: bool = False, **props: Any) -> Column:
    if not isinstance(collapsed, bool):
        raise TypeError("Sidebar collapsed must be a bool.")
    props.setdefault("width", 72 if collapsed else 240)
    props.setdefault("padding", 12)
    props.setdefault("class_name", "nova-sidebar")
    return Column(*children, **props)


def MainContent(*children: Component, **props: Any) -> Column:
    props.setdefault("padding", 24)
    props.setdefault("min_width", 0)
    props.setdefault("class_name", "nova-main-content")
    return Column(*children, **props)


def Footer(*children: Component, **props: Any) -> Row:
    props.setdefault("padding", 12)
    props.setdefault("class_name", "nova-footer")
    return Row(*children, align="center", **props)


def NavigationItem(label: str, href: str, *, active: bool = False) -> Component:
    from .components import Button

    if not isinstance(label, str) or not label:
        raise ValueError("NavigationItem label must be a non-empty string.")
    if not isinstance(href, str) or not href.startswith("/"):
        raise ValueError("NavigationItem href must be an application path beginning with '/'.")
    if not isinstance(active, bool):
        raise TypeError("NavigationItem active must be a bool.")
    return Button(
        label,
        on_click=lambda: navigate(href),
        variant="primary" if active else "secondary",
        class_name="nova-navigation-item active" if active else "nova-navigation-item",
    )


def Breadcrumbs(items: Sequence[str | tuple[str, str]]) -> Row:
    children: list[Component] = []
    for index, item in enumerate(items):
        if index:
            children.append(Text("/", color="#6b7280"))
        if isinstance(item, str):
            children.append(Text(item))
        elif (
            isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
            and isinstance(item[1], str) and item[1].startswith("/")
        ):
            children.append(NavigationItem(item[0], item[1]))
        else:
            raise ValueError("Breadcrumb items must be labels or (label, application_path) pairs.")
    return Row(*children, spacing=8, align="center", class_name="nova-breadcrumbs")


class Tabs(Component):
    """Accessible tab strip that serializes only the selected tab panel."""

    def __init__(self, tabs: Mapping[str, Component], *, selected: str | State[str] | None = None,
                 **props: Any):
        super().__init__(**props)
        if not isinstance(tabs, Mapping) or not tabs:
            raise ValueError("Tabs requires a non-empty mapping of labels to components.")
        if any(not isinstance(label, str) or not label for label in tabs):
            raise ValueError("Tab labels must be non-empty strings.")
        if any(not isinstance(panel, Component) for panel in tabs.values()):
            raise TypeError("Every tab panel must be a NovaUI Component.")
        self.tabs = dict(tabs)
        initial = next(iter(self.tabs)) if selected is None else (selected.value if isinstance(selected, State) else selected)
        if initial not in self.tabs:
            raise ValueError("Selected tab must match a configured tab label.")
        self._owns_state = not isinstance(selected, State)
        self._selected = selected if isinstance(selected, State) else state(initial)
        if not isinstance(self._selected.value, str) or self._selected.value not in self.tabs:
            raise ValueError("Selected tab state must contain a configured tab label.")
        self._handlers = {label: self._make_handler(label) for label in self.tabs}

    def _make_handler(self, label: str):
        def select() -> None:
            self._selected.value = label
        return select

    @property
    def selected(self) -> str:
        return self._selected.value

    def iter_children(self) -> tuple[Component, ...]:
        return tuple(self.tabs.values())

    def dispose(self) -> None:
        if self._owns_state:
            self._selected.dispose()

    def to_dict(self, register_event):
        selected = self.selected
        if selected not in self.tabs:
            raise ValueError("Selected tab state must match a configured tab label.")
        return {
            "id": self._node_id(),
            "type": "tabs",
            "selected": selected,
            "tabs": [
                {"label": label, "event_id": register_event(self._handlers[label]), "active": label == selected}
                for label in self.tabs
            ],
            "children": [self.tabs[selected].to_dict(register_event)],
            **self._common_props(),
        }
