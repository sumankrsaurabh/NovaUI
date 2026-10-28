from __future__ import annotations

import re
import runpy
import subprocess
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
        "Text", "Image", "Button", "Input", "NumberField", "SearchField", "RadioGroup", "MultiSelect",
        "Row", "Column", "Card", "Center", "Container", "Grid", "SplitPane", "ScrollView", "Stack",
        "Wrap", "Spacer", "StickyHeader", "DataTable",
        "ColumnDef", "RowAction", "Field", "Form", "Router", "AppShell", "Header",
        "Sidebar", "MainContent", "Footer", "NavigationItem", "Breadcrumbs", "Tabs",
        "Alert", "Dialog", "Spinner", "Toast", "ToastHost", "Theme", "CustomComponent", "WindowOptions",
        "DataGrid", "BulkAction", "CommandPalette", "TreeView", "Toolbar", "StatusBar", "FileUpload",
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


def test_file_upload_example_uses_system_glass_theme_and_responsive_card(monkeypatch):
    captured = {}

    def capture(root, **kwargs):
        captured["tree"] = root.to_dict(lambda callback: "event")
        captured["theme"] = kwargs["theme"]

    monkeypatch.setattr(ui, "app", capture)
    example = ROOT / "examples" / "file_upload.py"
    runpy.run_path(str(example), run_name="__main__")

    tree = captured["tree"]
    assert captured["theme"].mode == "system"
    assert captured["theme"].appearance == "glass"
    assert tree["type"] == "column"
    upload_card = tree["children"][2]
    assert upload_card["type"] == "card"
    assert upload_card["variant"] == "glass-strong"
    assert any(child["type"] == "file_upload" for child in upload_card["children"][0]["children"])
    details = tree["children"][3]
    assert details["type"] == "grid"
    assert details["mobile_columns"] == 1


def test_generated_component_reference_matches_real_constructors():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_component_reference.py"), "--check"],
        cwd=ROOT,
        check=True,
    )
