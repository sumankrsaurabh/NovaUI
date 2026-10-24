"""Context for project-scoped runtime paths selected by the CLI."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

_project_root: ContextVar[Path | None] = ContextVar("novaui_project_root", default=None)


def current_project_root() -> Path | None:
    return _project_root.get()


@contextmanager
def use_project_root(path: Path) -> Iterator[None]:
    token = _project_root.set(path.resolve())
    try:
        yield
    finally:
        _project_root.reset(token)
