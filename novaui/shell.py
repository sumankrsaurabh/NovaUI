"""Small application-shell compositions built from existing layout components."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlsplit

from .components import Column, Component, Row, Text, _ICON_NAMES
from .routing import current_route_path, navigate
from .state import State, state


def AppShell(*children: Component, **props: Any) -> Row:
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


def NavigationItem(label: str, href: str, *, active: bool = False, icon: str | None = None) -> Component:
    from .components import Button

    if not isinstance(label, str) or not label:
        raise ValueError("NavigationItem label must be a non-empty string.")
    if not isinstance(href, str) or not href.startswith("/"):
        raise ValueError("NavigationItem href must be an application path beginning with '/'.")
    if not isinstance(active, bool):
        raise TypeError("NavigationItem active must be a bool.")
    if icon is not None and not isinstance(icon, str):
        raise TypeError("NavigationItem icon must be a built-in icon name or None.")
    return Button(
        label,
        on_click=lambda: navigate(href),
        variant="secondary",
        icon=icon,
        class_name="nova-navigation-item active" if active else "nova-navigation-item",
    )


class _Navigation(Component):
    """Semantic navigation landmark with framework-rendered children."""

    def __init__(self, *items: Component, label: str, orientation: str, **props: Any):
        super().__init__(**props)
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Navigation landmark label must be a non-empty string.")
        if not isinstance(orientation, str) or orientation not in {"horizontal", "vertical"}:
            raise ValueError("Navigation orientation must be horizontal or vertical.")
        if any(not isinstance(item, Component) for item in items):
            raise TypeError("Navigation children must be NovaUI components.")
        self.items = items
        self.label = label.strip()
        self.orientation = orientation

    def iter_children(self) -> tuple[Component, ...]:
        return self.items

    def to_dict(self, register_event):
        return {
            "id": self._node_id(),
            "type": "navigation",
            "label": self.label,
            "orientation": self.orientation,
            **self._common_props(),
            "children": [item.to_dict(register_event) for item in self.items],
        }


class NavigationBar(_Navigation):
    """Responsive horizontal navigation landmark, typically used in an app bar."""

    def __init__(self, *items: Component, label: str = "Primary navigation", **props: Any):
        props.setdefault("class_name", "nova-navigation-bar")
        super().__init__(*items, label=label, orientation="horizontal", **props)


class SideNavigation(_Navigation):
    """Vertical navigation landmark for a sidebar or compact rail."""

    def __init__(self, *items: Component, label: str = "Side navigation", **props: Any):
        props.setdefault("class_name", "nova-side-navigation")
        super().__init__(*items, label=label, orientation="vertical", **props)


Navbar = NavigationBar


@dataclass(frozen=True)
class NavDestination:
    """One route shown by a responsive ``Scaffold`` navigation rail."""

    label: str
    href: str
    icon: str | None = None
    badge: str | int | None = None


class Scaffold(Component):
    """Fill the app window and adapt navigation to desktop, tablet, and mobile.

    Place a ``Scaffold`` inside the active app's root ``Router`` to get route
    highlighting and event-driven navigation. On wide screens destinations
    appear in a labeled sidebar, on tablet widths in an icon rail, and on
    mobile in a fixed bottom bar.
    """

    def __init__(
        self,
        body: Component,
        *,
        destinations: Sequence[NavDestination],
        top_bar: Component | None = None,
        brand: Component | None = None,
        floating_action: Component | None = None,
        current_path: str | None = None,
        label: str = "Primary navigation",
        sidebar_width: int = 256,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        if not isinstance(body, Component):
            raise TypeError("Scaffold body must be a NovaUI Component.")
        for name, value in (("top_bar", top_bar), ("brand", brand), ("floating_action", floating_action)):
            if value is not None and not isinstance(value, Component):
                raise TypeError(f"Scaffold {name} must be a NovaUI Component or None.")
        if not isinstance(destinations, Sequence) or isinstance(destinations, (str, bytes)):
            raise TypeError("Scaffold destinations must be a sequence of NavDestination values.")
        if not 1 <= len(destinations) <= 8 or any(not isinstance(item, NavDestination) for item in destinations):
            raise ValueError("Scaffold requires 1 to 8 NavDestination values.")
        hrefs: set[str] = set()
        for item in destinations:
            if not isinstance(item.label, str) or not item.label.strip():
                raise ValueError("Navigation destination labels must be non-empty strings.")
            if not isinstance(item.href, str) or not item.href.startswith("/"):
                raise ValueError("Navigation destination hrefs must be app paths beginning with '/'.")
            parsed = urlsplit(item.href)
            decoded_path = unquote(parsed.path, errors="strict")
            if (
                parsed.scheme or parsed.netloc or "?" in item.href or "#" in item.href
                or "\\" in item.href or "\x00" in decoded_path
                or any(part == ".." for part in decoded_path.split("/"))
            ):
                raise ValueError("Navigation destination hrefs must be local paths without query strings.")
            if item.href in hrefs:
                raise ValueError(f"Scaffold contains a duplicate destination path: {item.href!r}.")
            hrefs.add(item.href)
            if item.icon is not None and (not isinstance(item.icon, str) or item.icon not in _ICON_NAMES):
                raise ValueError(f"Navigation icon must be one of: {', '.join(sorted(_ICON_NAMES))}.")
            if item.badge is not None and (
                isinstance(item.badge, bool) or not isinstance(item.badge, (str, int))
            ):
                raise TypeError("Navigation badge must be a string, integer, or None.")
        if current_path is not None and (not isinstance(current_path, str) or not current_path.startswith("/")):
            raise ValueError("Scaffold current_path must be an app path beginning with '/' or None.")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Scaffold navigation label must be a non-empty string.")
        if isinstance(sidebar_width, bool) or not isinstance(sidebar_width, int) or not 200 <= sidebar_width <= 360:
            raise ValueError("Scaffold sidebar_width must be an integer from 200 to 360 pixels.")

        self.body = body
        self.top_bar = top_bar
        self.brand = brand
        self.floating_action = floating_action
        self.destinations = tuple(destinations)
        self.current_path = current_path
        self.label = label.strip()
        self.sidebar_width = sidebar_width
        self._handlers = tuple(self._make_handler(item.href) for item in self.destinations)
        self.class_name = "nova-scaffold" if self.class_name is None else f"nova-scaffold {self.class_name}"

    @staticmethod
    def _make_handler(href: str):
        def select() -> None:
            navigate(href)
        return select

    def iter_children(self) -> tuple[Component, ...]:
        return tuple(item for item in (self.brand, self.top_bar, self.body, self.floating_action) if item is not None)

    def to_dict(self, register_event):
        active_path = self.current_path or current_route_path() or "/"
        active_path = urlsplit(active_path).path.rstrip("/") or "/"
        destinations = []
        for item, handler in zip(self.destinations, self._handlers, strict=True):
            href_path = item.href.rstrip("/") or "/"
            active = active_path == href_path or (href_path != "/" and active_path.startswith(href_path + "/"))
            destinations.append({
                "label": item.label,
                "href": item.href,
                "icon": item.icon,
                "badge": item.badge,
                "active": active,
                "event_id": register_event(handler),
            })
        return {
            "id": self._node_id(),
            "type": "scaffold",
            "label": self.label,
            "sidebar_width": self.sidebar_width,
            "destinations": destinations,
            "brand": self.brand.to_dict(register_event) if self.brand else None,
            "top_bar": self.top_bar.to_dict(register_event) if self.top_bar else None,
            "body": self.body.to_dict(register_event),
            "floating_action": self.floating_action.to_dict(register_event) if self.floating_action else None,
            **self._common_props(),
        }


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
