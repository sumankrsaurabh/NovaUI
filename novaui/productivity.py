"""Command and navigation components for productivity-oriented screens."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from .components import Component, _children_dict

_TREE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True)
class Command:
    """A named action registered with a :class:`CommandPalette`."""

    label: str
    on_execute: Callable[[], Any]
    keywords: tuple[str, ...] = ()
    description: str | None = None
    shortcut: str | None = None

    def validate(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("Command label must be a non-empty string.")
        if not callable(self.on_execute):
            raise TypeError("Command on_execute must be callable.")
        if (not isinstance(self.keywords, tuple)
                or any(not isinstance(keyword, str) for keyword in self.keywords)):
            raise TypeError("Command keywords must be a tuple of strings.")
        if self.description is not None and not isinstance(self.description, str):
            raise TypeError("Command description must be a string or None.")
        if self.shortcut is not None and not isinstance(self.shortcut, str):
            raise TypeError("Command shortcut must be a string or None.")


class CommandPalette(Component):
    """A searchable list of explicitly registered application commands."""

    def __init__(
        self,
        commands: Sequence[Command],
        *,
        placeholder: str = "Search commands",
        empty_message: str = "No matching commands.",
        **props: Any,
    ):
        super().__init__(**props)
        self.commands = tuple(commands)
        self.placeholder = placeholder
        self.empty_message = empty_message

    def to_dict(self, register_event: Callable[[Callable[..., Any]], str]) -> dict[str, Any]:
        if any(not isinstance(command, Command) for command in self.commands):
            raise TypeError("CommandPalette commands must contain Command instances.")
        for command in self.commands:
            command.validate()
        if not isinstance(self.placeholder, str) or not isinstance(self.empty_message, str):
            raise TypeError("CommandPalette placeholder and empty_message must be strings.")
        return {
            "id": self._node_id(),
            "type": "command_palette",
            "placeholder": self.placeholder,
            "empty_message": self.empty_message,
            "commands": [
                {
                    "label": command.label,
                    "description": command.description,
                    "keywords": list(command.keywords),
                    "shortcut": command.shortcut,
                    "event_id": register_event(command.on_execute),
                }
                for command in self.commands
            ],
            **self._common_props(),
        }


@dataclass(frozen=True)
class TreeNode:
    """A labeled node in a :class:`TreeView`."""

    label: str
    children: Sequence[TreeNode] = ()
    key: str | None = None
    expanded: bool = False
    on_select: Callable[[TreeNode], Any] | None = None

    def validate(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("TreeNode label must be a non-empty string.")
        if (not isinstance(self.children, Sequence) or isinstance(self.children, (str, bytes))
                or any(not isinstance(child, TreeNode) for child in self.children)):
            raise TypeError("TreeNode children must be a sequence of TreeNode instances.")
        if self.key is not None and (
            not isinstance(self.key, str) or not _TREE_KEY.fullmatch(self.key)
        ):
            raise ValueError("TreeNode key must contain only letters, numbers, '.', '_', or '-'.")
        if not isinstance(self.expanded, bool):
            raise TypeError("TreeNode expanded must be a bool.")
        if self.on_select is not None and not callable(self.on_select):
            raise TypeError("TreeNode on_select must be callable or None.")


class TreeView(Component):
    """A keyboard-navigable tree with independently expandable branches."""

    def __init__(self, nodes: Sequence[TreeNode], *, label: str = "Tree", **props: Any):
        super().__init__(**props)
        self.nodes = tuple(nodes)
        self.label = label
        self._expanded: set[str] = set()
        self._initialized = False

    def to_dict(self, register_event: Callable[[Callable[..., Any]], str]) -> dict[str, Any]:
        if any(not isinstance(node, TreeNode) for node in self.nodes):
            raise TypeError("TreeView nodes must contain TreeNode instances.")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("TreeView label must be a non-empty string.")
        seen: set[str] = set()

        def serialize(nodes: tuple[TreeNode, ...], prefix: str = "") -> list[dict[str, Any]]:
            result = []
            for index, node in enumerate(nodes):
                node.validate()
                key = node.key or f"{prefix}{index}"
                if key in seen:
                    raise ValueError(f"TreeView node keys must be unique; duplicate {key!r}.")
                seen.add(key)
                if not self._initialized and node.expanded:
                    self._expanded.add(key)
                children = serialize(tuple(node.children), f"{key}.")
                has_children = bool(children)
                result.append({
                    "key": key,
                    "label": node.label,
                    "children": children,
                    "expanded": key in self._expanded,
                    "select_event_id": (
                        register_event(lambda selected=node: selected.on_select(selected))
                        if node.on_select is not None else None
                    ),
                    "toggle_event_id": register_event(lambda current=key: self._toggle(current))
                    if has_children else None,
                })
            return result

        nodes = serialize(self.nodes)
        self._initialized = True
        return {
            "id": self._node_id(),
            "type": "tree_view",
            "label": self.label,
            "nodes": nodes,
            **self._common_props(),
        }

    def _toggle(self, key: str) -> None:
        if key in self._expanded:
            self._expanded.remove(key)
        else:
            self._expanded.add(key)


class Toolbar(Component):
    """A semantic toolbar containing ordinary NovaUI controls."""

    def __init__(
        self,
        *children: Component,
        label: str = "Toolbar",
        orientation: str = "horizontal",
        **props: Any,
    ):
        super().__init__(**props)
        self.children = children
        self.label = label
        self.orientation = orientation

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event: Callable[[Callable[..., Any]], str]) -> dict[str, Any]:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("Toolbar label must be a non-empty string.")
        if self.orientation not in {"horizontal", "vertical"}:
            raise ValueError("Toolbar orientation must be 'horizontal' or 'vertical'.")
        return {
            "id": self._node_id(),
            "type": "toolbar",
            "label": self.label,
            "orientation": self.orientation,
            "children": _children_dict(self.children, register_event),
            **self._common_props(),
        }


class StatusBar(Component):
    """A semantic status region containing status text or controls."""

    def __init__(self, *children: Component, label: str = "Status", **props: Any):
        super().__init__(**props)
        self.children = children
        self.label = label

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event: Callable[[Callable[..., Any]], str]) -> dict[str, Any]:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("StatusBar label must be a non-empty string.")
        return {
            "id": self._node_id(),
            "type": "status_bar",
            "label": self.label,
            "children": _children_dict(self.children, register_event),
            **self._common_props(),
        }
