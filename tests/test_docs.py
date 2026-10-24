from __future__ import annotations

import re
import runpy
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import novaui as ui

ROOT = Path(__file__).resolve().parents[1]
_MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def test_repository_markdown_relative_links_resolve():
    markdown_files = [ROOT / "README.md", *ROOT.glob("*.md"), *ROOT.joinpath("docs").rglob("*.md")]
    for source in set(markdown_files):
        content = source.read_text(encoding="utf-8")
        for raw_target in _MARKDOWN_LINK.findall(content):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            parsed = urlparse(target)
            if parsed.scheme or parsed.netloc or target.startswith("//"):
                continue
            path = unquote(parsed.path)
            if not path:
                continue
            resolved = (source.parent / path).resolve()
            assert resolved.exists(), f"Broken link in {source.relative_to(ROOT)}: {target}"


def test_public_component_exports_are_mentioned_in_reference():
    reference = (ROOT / "COMPONENTS.md").read_text(encoding="utf-8")
    documented = (
        "Text", "Image", "Button", "Input", "Row", "Column", "Card", "Center",
        "Container", "Grid", "ScrollView", "Stack", "Wrap", "Spacer", "DataTable",
        "ColumnDef", "RowAction", "Field", "Form", "Router", "AppShell", "Header",
        "Sidebar", "MainContent", "Footer", "NavigationItem", "Breadcrumbs", "Tabs",
        "Alert", "Dialog", "Spinner", "Theme", "CustomComponent", "WindowOptions",
        "Menu", "MenuItem", "MenuSeparator", "ShortcutRegistry",
    )
    for name in documented:
        assert f"`{name}" in reference, f"Missing public component reference entry: {name}"


def test_examples_compile_and_serialize_initial_tree(monkeypatch):
    monkeypatch.setattr(ui.App, "run", lambda application, *args, **kwargs: application.serialize_tree())
    original_argv = sys.argv[:]
    try:
        for example in sorted((ROOT / "examples").glob("*.py")):
            sys.argv = [str(example)]
            runpy.run_path(str(example), run_name="__main__")
    finally:
        sys.argv = original_argv
