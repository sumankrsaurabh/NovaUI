"""Component definitions for the NovaUI MVP."""

from __future__ import annotations

import itertools
import inspect
import re
from contextvars import ContextVar
from functools import wraps
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, ParamSpec, cast
from urllib.parse import quote

from .state import State, track_dependencies

_component_ids = itertools.count(1)


_LENGTH_PATTERN = re.compile(
    r"^-?(?:\d+(?:\.\d+)?|\.\d+)(?:px|rem|em|%|vh|vw|vmin|vmax|ch|ex)$|^(?:0|auto|min-content|max-content|fit-content)$",
    re.IGNORECASE,
)
_CLASS_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*(?:\s+[A-Za-z_][A-Za-z0-9_-]*)*$")
_STYLE_PROPERTIES = {
    "align-items", "background-color", "border", "border-radius", "box-shadow", "color",
    "cursor", "display", "flex", "font-family", "font-size", "font-weight", "gap",
    "grid-template-columns", "justify-content", "letter-spacing", "line-height", "margin",
    "opacity", "overflow", "overflow-x", "overflow-y", "padding", "text-align", "white-space",
}
_UNITLESS_STYLE_PROPERTIES = {"flex", "font-weight", "line-height", "opacity"}
_UNSAFE_CSS_PATTERN = re.compile(r"url\s*\(|expression\s*\(|javascript\s*:", re.IGNORECASE)
_ICON_NAMES = frozenset({
    "home", "grid", "search", "settings", "plus", "minus", "arrow_right",
    "chevron_right", "chart", "users", "file", "check", "close", "menu",
    "sun", "moon", "sparkles", "download", "folder", "heart", "clock", "cube",
})
_ComponentParams = ParamSpec("_ComponentParams")
_component_scopes: ContextVar[tuple[list["Component"], ...]] = ContextVar("novaui_component_scopes", default=())


def _css_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{name} must be a non-empty CSS string.")
    if any(token in value for token in (";", "{", "}", "<", ">")) or _UNSAFE_CSS_PATTERN.search(value):
        raise ValueError(f"{name} contains an unsupported or unsafe CSS value.")
    return value.strip()


def _css_length(value: Any, name: str, *, allow_negative: bool = False,
                allow_shorthand: bool = False) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 0 and not allow_negative:
            raise ValueError(f"{name} must be non-negative.")
        return f"{value}px"
    if isinstance(value, str):
        parts = value.strip().split()
        valid_count = len(parts) <= 4 if allow_shorthand else len(parts) == 1
        if valid_count and parts and all(_LENGTH_PATTERN.fullmatch(part) for part in parts):
            if not allow_negative and any(part.startswith("-") for part in parts):
                raise ValueError(f"{name} must be non-negative.")
            return " ".join(parts)
    raise TypeError(f"{name} must be a pixel integer or a supported CSS length string.")


@dataclass(kw_only=True, eq=False)
class Component:
    """Base class for serializable UI components."""

    margin: int | str | None = None
    min_width: int | str | None = None
    max_width: int | str | None = None
    min_height: int | str | None = None
    max_height: int | str | None = None
    background: str | None = None
    border: str | None = None
    shadow: str | None = None
    visible: bool = True
    class_name: str | None = None
    style: dict[str, str | int | float] | None = None
    _nova_node_id: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Function components use this scoped construction log to infer a root
        # when their body composes components without an explicit return.
        for scope in _component_scopes.get():
            scope.append(self)

    def _node_id(self) -> str:
        node_id = self._nova_node_id
        if node_id is None:
            node_id = f"nova-{next(_component_ids)}"
            self._nova_node_id = node_id
        return node_id

    def _common_props(self) -> dict[str, Any]:
        styles: dict[str, str] = {}
        for name in ("margin", "min_width", "max_width", "min_height", "max_height"):
            value = getattr(self, name)
            if value is not None:
                styles[name.replace("_", "-")] = _css_length(
                    value, f"Component {name}", allow_negative=name == "margin", allow_shorthand=name == "margin"
                )
        for name in ("background", "border", "shadow"):
            value = getattr(self, name)
            if value is not None:
                css_name = {"background": "background", "border": "border", "shadow": "box-shadow"}[name]
                styles[css_name] = _css_text(value, f"Component {name}")
        if not isinstance(self.visible, bool):
            raise TypeError("Component visible must be a bool.")
        if self.class_name is not None and (
            not isinstance(self.class_name, str) or not _CLASS_PATTERN.fullmatch(self.class_name)
        ):
            raise ValueError("Component class_name must contain valid CSS class names separated by spaces.")
        if self.style is not None:
            if not isinstance(self.style, dict):
                raise TypeError("Component style must be a dictionary of supported CSS properties.")
            for name, value in self.style.items():
                if not isinstance(name, str) or name not in _STYLE_PROPERTIES:
                    raise ValueError(f"Unsupported component style property: {name!r}.")
                if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                    raise TypeError(f"Component style {name!r} must be a string or number.")
                if isinstance(value, (int, float)):
                    if not float("-inf") < float(value) < float("inf"):
                        raise ValueError(f"Component style {name!r} must be finite.")
                    styles[name] = str(value) if name in _UNITLESS_STYLE_PROPERTIES else f"{value}px"
                else:
                    styles[name] = _css_text(value, f"Component style {name!r}")
        return {"styles": styles, "visible": self.visible, "class_name": self.class_name}

    def to_dict(self, register_event: Callable[[Callable[..., Any]], str]) -> dict[str, Any]:
        raise NotImplementedError

    def iter_children(self) -> tuple[Component, ...]:
        return ()

    def dispose(self) -> None:
        """Release resources owned by this component, if any."""


def component(function: Callable[_ComponentParams, Component | None]) -> Callable[_ComponentParams, Component]:
    """Declare a reusable Python function that constructs a NovaUI component.

    The function may accept normal Python arguments. It can either return one
    :class:`Component` or construct exactly one component root in its body. The
    returned component is rendered and disposed by NovaUI's usual lifecycle.
    """
    if not inspect.isfunction(function):
        raise TypeError("@component can decorate only a Python function.")
    if inspect.iscoroutinefunction(function):
        raise TypeError("Component factories must be synchronous.")

    @wraps(function)
    def build_component(*args: Any, **kwargs: Any) -> Component:
        scopes = _component_scopes.get()
        constructed: list[Component] = []
        token = _component_scopes.set((*scopes, constructed))
        try:
            result = function(*args, **kwargs)
        finally:
            _component_scopes.reset(token)
        if result is None:
            constructed_ids = {id(item) for item in constructed}
            child_ids = {
                id(child)
                for parent in constructed
                for child in parent.iter_children()
                if isinstance(child, Component) and id(child) in constructed_ids
            }
            roots = [item for item in constructed if id(item) not in child_ids]
            if len(roots) == 1:
                result = roots[0]
            elif not roots:
                raise TypeError(
                    f"Component factory {function.__name__!r} did not return or compose a NovaUI Component."
                )
            else:
                result = Fragment(*roots)
        if not isinstance(result, Component):
            raise TypeError(
                f"Component factory {function.__name__!r} must return or compose a NovaUI Component, "
                f"not {type(result).__name__}."
            )
        return result

    setattr(build_component, "__novaui_component__", True)
    return cast(Callable[_ComponentParams, Component], build_component)


def _children_dict(children: tuple[Any, ...], register_event: Callable) -> list[dict[str, Any]]:
    result = []
    for child in children:
        if not isinstance(child, Component):
            raise TypeError(f"Expected a NovaUI Component, got {type(child).__name__}")
        result.append(child.to_dict(register_event))
    return result


def _dimension_props(component: Component) -> dict[str, int | None]:
    dimensions: dict[str, int | None] = {}
    for name in ("width", "height"):
        value = getattr(component, name, None)
        _nonnegative_integer(value, f"Component {name}", optional=True)
        dimensions[name] = value
    return dimensions


def _nonnegative_integer(value: Any, name: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, int) or isinstance(value, bool):
        qualifier = " or None" if optional else ""
        raise TypeError(f"{name} must be a non-negative integer{qualifier}.")
    if value < 0:
        raise ValueError(f"{name} must be non-negative.")


class _InputBinding:
    """Internal value-taking handler used only by state-bound inputs."""

    accepts_value = True

    def __init__(self, owner: Input):
        self._owner = owner

    def __call__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Input value must be a string.")
        if isinstance(self._owner.value, State):
            self._owner.value.update(value)
        else:
            self._owner.value = value
        if self._owner.on_change is not None:
            error = self._owner.on_change(value)
            if error is not None and not isinstance(error, str):
                raise TypeError("Input on_change must return a string error message or None.")
            self._owner.error = error


@dataclass
class Text(Component):
    text: str | Callable[[], Any]
    size: int | None = None
    bold: bool = False
    color: str | None = None
    width: int | None = None
    height: int | None = None
    _cached_text: str | None = field(default=None, init=False, repr=False, compare=False)
    _dependency_unsubscribers: list[Callable[[], None]] = field(
        default_factory=list, init=False, repr=False, compare=False
    )
    _disposed: bool = field(default=False, init=False, repr=False, compare=False)

    def _invalidate(self, _value: Any) -> None:
        self._cached_text = None

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        for unsubscribe in self._dependency_unsubscribers:
            unsubscribe()
        self._dependency_unsubscribers.clear()

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if not isinstance(self.text, str) and not callable(self.text):
            raise TypeError("Text value must be a string or a zero-argument callable.")
        if self.size is not None:
            _nonnegative_integer(self.size, "Text size")
        if not isinstance(self.bold, bool):
            raise TypeError("Text bold must be a bool.")
        if self.color is not None and not isinstance(self.color, str):
            raise TypeError("Text color must be a string or None.")
        if self._disposed:
            raise RuntimeError("Text component has been disposed.")
        if not callable(self.text):
            rendered_text = str(self.text)
        elif self._cached_text is not None:
            rendered_text = self._cached_text
        else:
            with track_dependencies() as dependencies:
                rendered_text = str(self.text())
            for unsubscribe in self._dependency_unsubscribers:
                unsubscribe()
            self._dependency_unsubscribers = [
                dependency.subscribe(self._invalidate)
                for dependency in dependencies
                if not dependency.is_disposed
            ]
            if dependencies:
                self._cached_text = rendered_text
        return {"id": self._node_id(), "type": "text", "text": rendered_text,
                **dimensions,
                "size": self.size, "bold": self.bold, "color": self.color, **self._common_props()}


class Image(Component):
    """Display an image stored inside the application's ``assets/`` directory."""

    def __init__(self, src: str, alt: str, *, width: int | None = None, height: int | None = None, **props: Any):
        super().__init__(**props)
        self.src, self.alt = src, alt
        self.width, self.height = width, height

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if not isinstance(self.src, str) or not self.src or "\\" in self.src:
            raise ValueError("Image src must be a relative path inside the assets directory.")
        source = self.src.removeprefix("assets/")
        parts = PurePosixPath(source).parts
        if source.startswith("/") or not parts or any(part in {".", ".."} for part in parts):
            raise ValueError("Image src must not be absolute or traverse outside assets/.")
        if not isinstance(self.alt, str):
            raise TypeError("Image alt must be a string.")
        return {"id": self._node_id(), "type": "image", "src": "/assets/" + quote("/".join(parts), safe="/"),
                "alt": self.alt, **dimensions, **self._common_props()}


@dataclass
class Button(Component):
    label: str
    on_click: Callable[..., Any] | None = None
    disabled: bool = False
    variant: str = "primary"
    width: int | None = None
    height: int | None = None
    icon: str | None = None

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if not isinstance(self.label, str):
            raise TypeError("Button label must be a string.")
        if self.on_click is not None and not callable(self.on_click):
            raise TypeError("Button on_click must be callable or None.")
        if not isinstance(self.disabled, bool):
            raise TypeError("Button disabled must be a bool.")
        if self.variant not in {"primary", "secondary"}:
            raise ValueError("Button variant must be 'primary' or 'secondary'.")
        if self.icon is not None and self.icon not in _ICON_NAMES:
            raise ValueError(f"Button icon must be one of: {', '.join(sorted(_ICON_NAMES))}.")
        event_id = register_event(self.on_click) if self.on_click is not None and not self.disabled else None
        return {"id": self._node_id(), "type": "button", "label": self.label, "event_id": event_id,
                **dimensions, "disabled": self.disabled, "variant": self.variant, "icon": self.icon,
                **self._common_props()}


@dataclass
class Icon(Component):
    """A small, accessible icon from NovaUI's bundled stroke icon set."""

    name: str
    size: int = 18
    label: str | None = None

    def to_dict(self, register_event):
        if not isinstance(self.name, str) or self.name not in _ICON_NAMES:
            raise ValueError(f"Icon name must be one of: {', '.join(sorted(_ICON_NAMES))}.")
        if isinstance(self.size, bool) or not isinstance(self.size, int) or not 12 <= self.size <= 48:
            raise ValueError("Icon size must be an integer from 12 to 48 pixels.")
        if self.label is not None and (not isinstance(self.label, str) or not self.label.strip()):
            raise ValueError("Icon label must be a non-empty string or None.")
        return {"id": self._node_id(), "type": "icon", "name": self.name, "size": self.size,
                "label": self.label, **self._common_props()}


@dataclass
class IconButton(Component):
    """A compact button with a visible symbol and an accessible text label."""

    icon: str
    label: str
    on_click: Callable[..., Any] | None = None
    disabled: bool = False
    variant: str = "secondary"
    size: str = "medium"
    width: int | None = None
    height: int | None = None

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if not isinstance(self.icon, str) or not self.icon.strip() or len(self.icon) > 16:
            raise ValueError("IconButton icon must be a non-empty symbol of at most 16 characters.")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("IconButton label must be a non-empty accessible name.")
        if self.on_click is not None and not callable(self.on_click):
            raise TypeError("IconButton on_click must be callable or None.")
        if not isinstance(self.disabled, bool):
            raise TypeError("IconButton disabled must be a bool.")
        if self.variant not in {"primary", "secondary"}:
            raise ValueError("IconButton variant must be 'primary' or 'secondary'.")
        if self.size not in {"small", "medium", "large"}:
            raise ValueError("IconButton size must be 'small', 'medium', or 'large'.")
        event_id = register_event(self.on_click) if self.on_click is not None and not self.disabled else None
        return {"id": self._node_id(), "type": "icon_button", "icon": self.icon.strip(),
                "label": self.label.strip(), "event_id": event_id, "disabled": self.disabled,
                "variant": self.variant, "size": self.size, **dimensions, **self._common_props()}


@dataclass
class Badge(Component):
    """A compact status label with a semantic tone."""

    label: str
    tone: str = "neutral"

    def to_dict(self, register_event):
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("Badge label must be a non-empty string.")
        if self.tone not in {"neutral", "info", "success", "warning", "danger"}:
            raise ValueError("Badge tone must be neutral, info, success, warning, or danger.")
        return {"id": self._node_id(), "type": "badge", "label": self.label.strip(),
                "tone": self.tone, **self._common_props()}


@dataclass
class Divider(Component):
    """A semantic horizontal or vertical separator."""

    orientation: str = "horizontal"

    def to_dict(self, register_event):
        if self.orientation not in {"horizontal", "vertical"}:
            raise ValueError("Divider orientation must be 'horizontal' or 'vertical'.")
        return {"id": self._node_id(), "type": "divider", "orientation": self.orientation,
                **self._common_props()}


@dataclass
class ProgressBar(Component):
    """A determinate, accessible progress indicator."""

    value: int | float
    max_value: int | float = 100
    label: str = "Progress"
    show_value: bool = False

    def to_dict(self, register_event):
        if (isinstance(self.value, bool) or not isinstance(self.value, (int, float))
                or not float("-inf") < float(self.value) < float("inf")):
            raise TypeError("ProgressBar value must be a finite number.")
        if (isinstance(self.max_value, bool) or not isinstance(self.max_value, (int, float))
                or not float("-inf") < float(self.max_value) < float("inf") or self.max_value <= 0):
            raise ValueError("ProgressBar max_value must be a finite number greater than zero.")
        if self.value < 0 or self.value > self.max_value:
            raise ValueError("ProgressBar value must be between zero and max_value.")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("ProgressBar label must be a non-empty accessible name.")
        if not isinstance(self.show_value, bool):
            raise TypeError("ProgressBar show_value must be a bool.")
        return {"id": self._node_id(), "type": "progress_bar", "value": self.value,
                "max_value": self.max_value, "label": self.label.strip(),
                "show_value": self.show_value, **self._common_props()}


@dataclass
class Skeleton(Component):
    """An accessible-hidden placeholder for text, rectangular, or circular content."""

    variant: str = "text"
    width: int | None = None
    height: int | None = None
    lines: int = 1

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if self.variant not in {"text", "rect", "circle"}:
            raise ValueError("Skeleton variant must be 'text', 'rect', or 'circle'.")
        if not isinstance(self.lines, int) or isinstance(self.lines, bool) or not 1 <= self.lines <= 12:
            raise ValueError("Skeleton lines must be an integer from 1 to 12.")
        if self.variant != "text" and self.lines != 1:
            raise ValueError("Skeleton lines is supported only when variant='text'.")
        return {"id": self._node_id(), "type": "skeleton", "variant": self.variant,
                "lines": self.lines, **dimensions, **self._common_props()}


@dataclass
class Input(Component):
    placeholder: str = ""
    value: str | State[str] = ""
    password: bool = False
    label: str | None = None
    on_change: Callable[[str], str | None] | None = None
    disabled: bool = False
    read_only: bool = False
    error: str | None = None
    width: int | None = None
    height: int | None = None
    input_type: str | None = None
    name: str | None = None
    required: bool = False
    min_length: int | None = None
    max_length: int | None = None
    min_value: str | int | float | None = None
    max_value: str | int | float | None = None

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if not isinstance(self.placeholder, str):
            raise TypeError("Input placeholder must be a string.")
        if self.label is not None and not isinstance(self.label, str):
            raise TypeError("Input label must be a string or None.")
        if not all(isinstance(value, bool) for value in (self.password, self.disabled, self.read_only)):
            raise TypeError("Input password, disabled, and read_only values must be bools.")
        if not isinstance(self.required, bool):
            raise TypeError("Input required must be a bool.")
        input_type = "password" if self.password else (self.input_type or "text")
        if input_type not in {"text", "email", "password", "number", "date"}:
            raise ValueError("Input input_type must be text, email, password, number, or date.")
        if self.password and self.input_type not in {None, "password"}:
            raise ValueError("Input password=True cannot be combined with a different input_type.")
        if self.name is not None and (
            not isinstance(self.name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", self.name)
        ):
            raise ValueError("Input name must be a valid identifier of at most 64 characters.")
        for name in ("min_length", "max_length"):
            value = getattr(self, name)
            if value is not None:
                _nonnegative_integer(value, f"Input {name}")
        if self.min_length is not None and self.max_length is not None and self.min_length > self.max_length:
            raise ValueError("Input min_length cannot exceed max_length.")
        for name in ("min_value", "max_value"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (str, int, float))
                or isinstance(value, str) and not value.strip()
            ):
                raise TypeError(f"Input {name} must be a non-empty string or number.")
        if input_type == "number":
            for name in ("min_value", "max_value"):
                value = getattr(self, name)
                if value is not None:
                    try:
                        numeric_value = float(value)
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"Input {name} must be numeric for number inputs.") from exc
                    if not float("-inf") < numeric_value < float("inf"):
                        raise ValueError(f"Input {name} must be finite.")
            if self.min_value is not None and self.max_value is not None and float(self.min_value) > float(self.max_value):
                raise ValueError("Input min_value cannot exceed max_value.")
        if isinstance(self.value, State):
            current_value = self.value.value
            if not isinstance(current_value, str):
                raise TypeError("Input state must contain a string value.")
        elif isinstance(self.value, str):
            current_value = self.value
        else:
            raise TypeError("Input value must be a string or State[str].")
        if self.on_change is not None and not callable(self.on_change):
            raise TypeError("Input on_change must be callable.")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("Input error must be a string or None.")
        is_bound = isinstance(self.value, State) or self.on_change is not None
        event_id = None
        if is_bound and not self.disabled and not self.read_only:
            event_id = register_event(_InputBinding(self))
        return {"id": self._node_id(), "type": "input", "placeholder": self.placeholder,
                "value": current_value, "password": self.password, "label": self.label,
                "input_type": input_type, "name": self.name, "required": self.required,
                "min_length": self.min_length, "max_length": self.max_length,
                "min_value": str(self.min_value) if self.min_value is not None else None,
                "max_value": str(self.max_value) if self.max_value is not None else None,
                "event_id": event_id, "disabled": self.disabled, "read_only": self.read_only,
                "error": self.error, **dimensions, **self._common_props()}


class Row(Component):
    def __init__(self, *children: Component, spacing: int = 8, padding: int = 0, align: str = "center",
                 justify: str = "start", width: int | None = None, height: int | None = None, **props: Any):
        super().__init__(**props)
        self.children, self.spacing, self.padding, self.align = children, spacing, padding, align
        self.justify, self.width, self.height = justify, width, height

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        _nonnegative_integer(self.spacing, "Row spacing")
        _nonnegative_integer(self.padding, "Row padding")
        _validate_alignment(self.align, "Row align", {"start", "center", "end", "stretch", "baseline"})
        _validate_alignment(self.justify, "Row justify", {"start", "center", "end", "between", "around", "evenly"})
        return {"id": self._node_id(), "type": "row", "spacing": self.spacing, "padding": self.padding,
                **dimensions, "align": self.align, "justify": self.justify, **self._common_props(),
                "children": _children_dict(self.children, register_event)}


class Column(Component):
    def __init__(self, *children: Component, spacing: int = 8, padding: int = 0, align: str = "stretch",
                 justify: str = "start", width: int | None = None, height: int | None = None, **props: Any):
        super().__init__(**props)
        self.children, self.spacing, self.padding, self.align = children, spacing, padding, align
        self.justify, self.width, self.height = justify, width, height

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        _nonnegative_integer(self.spacing, "Column spacing")
        _nonnegative_integer(self.padding, "Column padding")
        _validate_alignment(self.align, "Column align", {"start", "center", "end", "stretch", "baseline"})
        _validate_alignment(self.justify, "Column justify", {"start", "center", "end", "between", "around", "evenly"})
        return {"id": self._node_id(), "type": "column", "spacing": self.spacing, "padding": self.padding,
                **dimensions, "align": self.align, "justify": self.justify, **self._common_props(),
                "children": _children_dict(self.children, register_event)}


class Card(Component):
    def __init__(self, *children: Component, padding: int = 16, radius: int | None = None,
                 variant: str = "auto",
                 width: int | None = None, height: int | None = None, **props: Any):
        super().__init__(**props)
        self.children, self.padding, self.radius, self.variant = children, padding, radius, variant
        self.width, self.height = width, height

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        _nonnegative_integer(self.padding, "Card padding")
        _nonnegative_integer(self.radius, "Card radius", optional=True)
        if not isinstance(self.variant, str) or self.variant not in {"auto", "solid", "glass", "glass-strong"}:
            raise ValueError("Card variant must be 'auto', 'solid', 'glass', or 'glass-strong'.")
        return {"id": self._node_id(), "type": "card", "padding": self.padding, "radius": self.radius,
                "variant": self.variant,
                **dimensions, **self._common_props(),
                "children": _children_dict(self.children, register_event)}


@dataclass
class Spacer(Component):
    size: int = 8
    width: int | None = None
    height: int | None = None

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        _nonnegative_integer(self.size, "Spacer size")
        return {"id": self._node_id(), "type": "spacer", "size": self.size, **dimensions,
                **self._common_props()}


class Center(Component):
    def __init__(self, child: Component, *, width: int | None = None, height: int | None = None,
                 **props: Any):
        super().__init__(**props)
        self.child = child
        self.width, self.height = width, height

    def iter_children(self) -> tuple[Component, ...]:
        return (self.child,) if isinstance(self.child, Component) else ()

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if not isinstance(self.child, Component):
            raise TypeError("Center child must be a NovaUI Component.")
        return {"id": self._node_id(), "type": "center", **dimensions,
                **self._common_props(),
                "children": [self.child.to_dict(register_event)]}


def _validate_alignment(value: Any, name: str, allowed: set[str]) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if value not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}.")


class Container(Component):
    """A single CSS box for sizing, spacing, and styling child components."""

    def __init__(self, *children: Component, padding: int = 0, width: int | None = None,
                 height: int | None = None, **props: Any):
        super().__init__(**props)
        self.children, self.padding, self.width, self.height = children, padding, width, height

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        _nonnegative_integer(self.padding, "Container padding")
        return {"id": self._node_id(), "type": "container", "padding": self.padding,
                **dimensions, **self._common_props(), "children": _children_dict(self.children, register_event)}


class Grid(Component):
    """A responsive CSS grid; integer columns use equal-width tracks."""

    def __init__(self, *children: Component, columns: int | str = 2, spacing: int = 8,
                 padding: int = 0, width: int | None = None, height: int | None = None, **props: Any):
        super().__init__(**props)
        self.children, self.columns, self.spacing, self.padding = children, columns, spacing, padding
        self.width, self.height = width, height

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if isinstance(self.columns, int) and not isinstance(self.columns, bool):
            if not 1 <= self.columns <= 12:
                raise ValueError("Grid columns must be an integer from 1 to 12.")
            columns = f"repeat({self.columns}, minmax(0, 1fr))"
        elif isinstance(self.columns, str):
            columns = _css_text(self.columns, "Grid columns")
        else:
            raise TypeError("Grid columns must be a positive integer or CSS grid template string.")
        _nonnegative_integer(self.spacing, "Grid spacing")
        _nonnegative_integer(self.padding, "Grid padding")
        return {"id": self._node_id(), "type": "grid", "columns": columns,
                "column_count": self.columns if isinstance(self.columns, int) else None, "spacing": self.spacing,
                "padding": self.padding, **dimensions, **self._common_props(),
                "children": _children_dict(self.children, register_event)}


class ScrollView(Component):
    """A container that scrolls vertically, horizontally, or in both directions."""

    def __init__(self, *children: Component, direction: str = "vertical", padding: int = 0,
                 width: int | None = None, height: int | None = None, **props: Any):
        super().__init__(**props)
        self.children, self.direction, self.padding = children, direction, padding
        self.width, self.height = width, height

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        if self.direction not in {"vertical", "horizontal", "both"}:
            raise ValueError("ScrollView direction must be 'vertical', 'horizontal', or 'both'.")
        _nonnegative_integer(self.padding, "ScrollView padding")
        return {"id": self._node_id(), "type": "scroll_view", "direction": self.direction,
                "padding": self.padding, **dimensions, **self._common_props(),
                "children": _children_dict(self.children, register_event)}


class Stack(Component):
    """Layer child components in the same CSS grid cell."""

    def __init__(self, *children: Component, width: int | None = None, height: int | None = None,
                 **props: Any):
        super().__init__(**props)
        self.children, self.width, self.height = children, width, height

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        return {"id": self._node_id(), "type": "stack", **dimensions, **self._common_props(),
                "children": _children_dict(self.children, register_event)}


class Wrap(Component):
    """Lay children out in rows that wrap when available width is exhausted."""

    def __init__(self, *children: Component, spacing: int = 8, run_spacing: int = 8,
                 align: str = "start", width: int | None = None, height: int | None = None,
                 **props: Any):
        super().__init__(**props)
        self.children, self.spacing, self.run_spacing, self.align = children, spacing, run_spacing, align
        self.width, self.height = width, height

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        dimensions = _dimension_props(self)
        _nonnegative_integer(self.spacing, "Wrap spacing")
        _nonnegative_integer(self.run_spacing, "Wrap run_spacing")
        _validate_alignment(self.align, "Wrap align", {"start", "center", "end", "stretch"})
        return {"id": self._node_id(), "type": "wrap", "spacing": self.spacing,
                "run_spacing": self.run_spacing, "align": self.align, **dimensions,
                **self._common_props(), "children": _children_dict(self.children, register_event)}


class Fragment(Component):
    """Group sibling components without adding a visual layout box."""

    def __init__(self, *children: Component):
        super().__init__()
        self.children = children

    def iter_children(self) -> tuple[Component, ...]:
        return self.children

    def to_dict(self, register_event):
        return {"id": self._node_id(), "type": "fragment",
                "children": _children_dict(self.children, register_event)}


class Animated(Component):
    """Render one child with a validated, one-time entrance animation.

    Exit animations are intentionally unsupported: the current renderer removes
    obsolete nodes immediately and has no asynchronous removal lifecycle.
    """

    PRESETS = frozenset({"fade", "fade_up", "fade_down", "slide_in", "scale_in", "pop"})
    EASINGS = frozenset({"linear", "ease", "ease-in", "ease-out", "ease-in-out"})

    def __init__(self, child: Component, *, enter: str = "fade", duration: int = 240,
                 easing: str = "ease-out", **props: Any):
        super().__init__(**props)
        self.child = child
        self.enter = enter
        self.duration = duration
        self.easing = easing

    def iter_children(self) -> tuple[Component, ...]:
        return (self.child,) if isinstance(self.child, Component) else ()

    def to_dict(self, register_event):
        if not isinstance(self.child, Component):
            raise TypeError("Animated child must be a NovaUI Component.")
        if self.enter not in self.PRESETS:
            raise ValueError(f"Animated enter must be one of: {', '.join(sorted(self.PRESETS))}.")
        if isinstance(self.duration, bool) or not isinstance(self.duration, int):
            raise TypeError("Animated duration must be an integer number of milliseconds.")
        if not 0 <= self.duration <= 2000:
            raise ValueError("Animated duration must be between 0 and 2000 milliseconds.")
        if self.easing not in self.EASINGS:
            raise ValueError(f"Animated easing must be one of: {', '.join(sorted(self.EASINGS))}.")
        return {"id": self._node_id(), "type": "animated", "enter": self.enter,
                "duration": self.duration, "easing": self.easing, **self._common_props(),
                "children": [self.child.to_dict(register_event)]}
