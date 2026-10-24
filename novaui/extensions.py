"""Explicit, per-application extension registration.

Extensions are trusted Python code. This module deliberately does not discover
or import installed packages automatically.
"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Callable
from typing import Any

from .components import Component, Container
from .theme import Theme

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class CustomComponent(Component):
    """Base for safe, compositional custom components.

    Subclasses implement :meth:`render` and return a tree of NovaUI components.
    The tree is built once per instance and participates in normal app lifecycle
    and event registration. Custom components cannot emit raw HTML or scripts.
    """

    def __init__(self, **props: Any) -> None:
        super().__init__(**props)
        self._rendered_content: Component | None = None
        self._rendered_root: Component | None = None

    def render(self) -> Component:
        raise NotImplementedError("CustomComponent subclasses must implement render().")

    def _tree(self) -> Component:
        if self._rendered_root is not None:
            return self._rendered_root
        if self._rendered_content is None:
            content = self.render()
            if not isinstance(content, Component):
                raise TypeError("CustomComponent.render() must return a NovaUI Component.")
            self._rendered_content = content
        styled = any((
            self.margin is not None, self.min_width is not None, self.max_width is not None,
            self.min_height is not None, self.max_height is not None, self.background is not None,
            self.border is not None, self.shadow is not None, not self.visible,
            self.class_name is not None, self.style is not None,
        ))
        if styled:
            self._rendered_root = Container(
                self._rendered_content,
                margin=self.margin,
                min_width=self.min_width,
                max_width=self.max_width,
                min_height=self.min_height,
                max_height=self.max_height,
                background=self.background,
                border=self.border,
                shadow=self.shadow,
                visible=self.visible,
                class_name=self.class_name,
                style=self.style,
            )
        else:
            self._rendered_root = self._rendered_content
        return self._rendered_root

    def iter_children(self) -> tuple[Component, ...]:
        return (self._tree(),)

    def to_dict(self, register_event: Callable[..., str]) -> dict[str, Any]:
        return self._tree().to_dict(register_event)


class Extensions:
    """Mutable extension configuration copied into each :class:`~novaui.App`.

    Register extension components, themes, and trusted plugin instances here,
    then pass it to ``App(..., extensions=...)`` or ``ui.app(..., extensions=...)``.
    """

    def __init__(self) -> None:
        self.components: dict[str, type[CustomComponent]] = {}
        self.themes: dict[str, Theme] = {}
        self.plugins: list[Any] = []

    def register_component(self, name: str, component: type[CustomComponent]) -> None:
        _validate_name(name, "component")
        if not isinstance(component, type) or not issubclass(component, CustomComponent) or component is CustomComponent:
            raise TypeError("Custom components must subclass ui.CustomComponent.")
        if name in self.components:
            raise ValueError(f"Custom component {name!r} is already registered.")
        self.components[name] = component

    def register_theme(self, theme: Theme) -> None:
        if not isinstance(theme, Theme) or not theme.name:
            raise TypeError("Registered themes must be Theme instances with a name.")
        if theme.name in self.themes:
            raise ValueError(f"Theme {theme.name!r} is already registered.")
        self.themes[theme.name] = theme

    def use(self, plugin: Any) -> None:
        """Add a plugin instance; its trusted ``setup(app)`` runs at app creation."""
        name = getattr(plugin, "name", None)
        _validate_name(name, "plugin")
        if any(getattr(existing, "name", None) == name for existing in self.plugins):
            raise ValueError(f"Plugin {name!r} is already registered.")
        setup = getattr(plugin, "setup", None)
        if setup is not None and not callable(setup):
            raise TypeError(f"Plugin {name!r} setup must be callable.")
        for hook in ("on_app_start", "on_app_stop"):
            callback = getattr(plugin, hook, None)
            if callback is not None and not callable(callback):
                raise TypeError(f"Plugin {name!r} {hook} must be callable.")
        if setup is None and not any(getattr(plugin, hook, None) is not None for hook in ("on_app_start", "on_app_stop")):
            raise TypeError(f"Plugin {name!r} must implement setup, on_app_start, or on_app_stop.")
        self.plugins.append(plugin)


def _validate_name(name: Any, kind: str) -> None:
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ValueError(f"{kind.capitalize()} name must start with a letter and contain at most 64 letters, digits, or underscores.")


def check_compatibility(plugin: Any, novaui_version: str) -> None:
    """Validate optional plugin version and import requirements.

    ``min_novaui_version`` is inclusive and ``max_novaui_version_exclusive``
    is exclusive. Version strings use ``major.minor.patch``.
    """
    current = _parse_version(novaui_version, "NovaUI")
    minimum = getattr(plugin, "min_novaui_version", None)
    maximum = getattr(plugin, "max_novaui_version_exclusive", None)
    if minimum is not None and current < _parse_version(minimum, "min_novaui_version"):
        raise RuntimeError(f"Plugin {plugin.name!r} requires NovaUI >= {minimum}.")
    if maximum is not None and current >= _parse_version(maximum, "max_novaui_version_exclusive"):
        raise RuntimeError(f"Plugin {plugin.name!r} requires NovaUI < {maximum}.")
    optional_dependencies = getattr(plugin, "optional_dependencies", ())
    if not isinstance(optional_dependencies, (tuple, list)):
        raise TypeError(f"Plugin {plugin.name!r} optional_dependencies must be a tuple or list of module names.")
    for module in optional_dependencies:
        if not isinstance(module, str) or not module:
            raise TypeError(f"Plugin {plugin.name!r} optional_dependencies must contain module names.")
        if importlib.util.find_spec(module) is None:
            raise RuntimeError(f"Plugin {plugin.name!r} requires optional dependency {module!r}; install it before enabling the plugin.")


def _parse_version(value: str, field: str) -> tuple[int, int, int]:
    match = _VERSION.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValueError(f"{field} must use major.minor.patch version format.")
    return tuple(map(int, match.groups()))
