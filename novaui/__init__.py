"""NovaUI: a Python-first declarative UI framework starter."""

from . import clipboard, dialogs, window
from .app import App, app, desktop
from .components import (
    Animated,
    Button,
    Card,
    Center,
    Column,
    Component,
    Container,
    Grid,
    Image,
    Input,
    Row,
    ScrollView,
    Spacer,
    Stack,
    Text,
    Wrap,
)
from .data_table import ColumnDef, DataTable, RowAction
from .desktop import Menu, MenuItem, MenuSeparator, WindowOptions
from .extensions import CustomComponent, Extensions
from .feedback import Alert, Dialog, Spinner
from .forms import Field, Form
from .routing import Router, navigate
from .shell import (
    AppShell,
    Breadcrumbs,
    Footer,
    Header,
    MainContent,
    NavigationItem,
    Sidebar,
    Tabs,
)
from .shortcuts import ShortcutRegistry
from .state import State, state
from .theme import Theme

__version__ = "0.1.0"

__all__ = [
    "Alert",
    "Animated",
    "App",
    "AppShell",
    "Breadcrumbs",
    "Button",
    "Card",
    "Center",
    "Column",
    "ColumnDef",
    "Component",
    "Container",
    "CustomComponent",
    "DataTable",
    "Dialog",
    "Extensions",
    "Field",
    "Footer",
    "Form",
    "Grid",
    "Header",
    "Image",
    "Input",
    "MainContent",
    "Menu",
    "MenuItem",
    "MenuSeparator",
    "NavigationItem",
    "Router",
    "Row",
    "RowAction",
    "ScrollView",
    "ShortcutRegistry",
    "Sidebar",
    "Spacer",
    "Spinner",
    "Stack",
    "State",
    "Tabs",
    "Text",
    "Theme",
    "WindowOptions",
    "Wrap",
    "__version__",
    "app",
    "clipboard",
    "desktop",
    "dialogs",
    "navigate",
    "state",
    "window",
]
