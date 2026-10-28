"""Command-line tools for creating, running, checking, and building NovaUI apps."""

from __future__ import annotations

import argparse
import ast
import json
import keyword
import logging
import os
import queue
import re
import runpy
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from . import __version__
from .project import use_project_root

_PROJECT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="novaui", description="Create and run NovaUI applications.")
    parser.add_argument("--version", action="version", version=f"novaui {__version__}")
    parser.add_argument("--debug", action="store_true", help="show detailed diagnostics")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="create a starter application")
    create.add_argument("name", help="new project directory name")
    create.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="show detailed diagnostics")

    run = commands.add_parser("run", help="run an application from this project")
    run.add_argument("script", nargs="?", type=Path, help="entry point (default: tool.novaui.entry or app.py)")
    run.add_argument("--mode", choices=("web", "desktop"), help="hosting mode (default: project config or web)")
    run.add_argument("--host", help="bind host (loopback only)")
    run.add_argument("--port", type=int, help="port from 0 to 65535; 0 chooses an available port")
    run.add_argument("--open-browser", action="store_true", help="open the app in the default browser")
    run.add_argument("--no-browser", action="store_true", help="do not open a browser")
    run.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="show detailed diagnostics")

    check = commands.add_parser("check", help="check Python syntax, imports, and project tests")
    check.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="show detailed diagnostics")
    build = commands.add_parser("build", help="build NovaUI source and wheel distributions")
    build.add_argument("--outdir", type=Path, default=Path("dist"), help="output directory (default: dist)")
    build.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="show detailed diagnostics")

    preview = commands.add_parser("preview", help="render a component preview from a Python source file")
    preview.add_argument("script", type=Path, help="Python file containing top-level @ui.preview functions")
    preview.add_argument("--name", help="select a preview by its registered name")
    preview.add_argument("--list", action="store_true", help="list previews and exit without rendering them")
    preview.add_argument("--theme", choices=("light", "dark"), help="override the preview theme")
    preview.add_argument("--host", choices=("127.0.0.1",), default="127.0.0.1", help=argparse.SUPPRESS)
    preview.add_argument("--port", type=int, default=0, help="loopback port (0 chooses an available port)")
    preview.add_argument("--no-browser", action="store_true", help="print the URL without opening a browser")
    preview.add_argument("--no-watch", action="store_true", help="disable source hot reload")
    preview.add_argument("--json-protocol", action="store_true", help=argparse.SUPPRESS)
    preview.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="show detailed diagnostics")
    return parser


def _preview_error(diagnostic) -> str:
    location = f" ({diagnostic.file}:{diagnostic.line})" if diagnostic.line else f" ({diagnostic.file})"
    return f"{diagnostic.error_type}: {diagnostic.message}{location}"


def _run_preview(args, project_dir: Path) -> int:
    from .preview import PreviewRuntime, parse_preview_command

    source = (project_dir / args.script).resolve() if not args.script.is_absolute() else args.script.resolve()
    if isinstance(args.port, bool) or not 0 <= args.port <= 65535:
        print("novaui: preview port must be between 0 and 65535.", file=sys.stderr)
        return 2
    runtime = PreviewRuntime(project_dir)
    try:
        discovery = runtime.discover_previews(source)
        if discovery.error:
            print(f"novaui: {_preview_error(discovery.error)}", file=sys.stderr)
            return 2
        if args.list:
            print(json.dumps({"version": 1, "type": "previews", "previews": [item.to_dict() for item in discovery.previews]}))
            return 0
        if args.name is None and len(discovery.previews) > 1:
            names = ", ".join(preview.name for preview in discovery.previews)
            print(f"novaui: this file has multiple previews; pass --name. Available: {names}", file=sys.stderr)
            return 2
        result = runtime.render_preview(source, args.name, theme=args.theme)
        if not result.ok:
            print(f"novaui: {_preview_error(result.error)}", file=sys.stderr)
            return 1
        url = runtime.start_server(port=args.port)
        if args.json_protocol:
            ready = {
                "version": 1,
                "type": "ready",
                "url": url,
                "selected": runtime.selected,
                "theme": runtime.theme,
                "viewport": {"width": runtime.viewport[0], "height": runtime.viewport[1]},
                "previews": [item.to_dict() for item in discovery.previews],
            }
            print("NOVAUI_PREVIEW " + json.dumps(ready), flush=True)
            runtime.on_loading = lambda: print(
                'NOVAUI_PREVIEW {"version":1,"type":"loading"}', flush=True
            )
            def report_change(update) -> None:
                print("NOVAUI_PREVIEW " + json.dumps({
                    "version": 1,
                    "type": "update",
                    **update.to_dict(),
                }), flush=True)
            runtime.on_change = report_change
        else:
            print(f"NovaUI preview running at {url} (Ctrl+C to stop)", flush=True)
            if not args.no_browser:
                webbrowser.open(url)

        if not args.no_watch:
            runtime.start_watching()

        commands: queue.Queue[str] = queue.Queue()
        idle = threading.Event()
        if args.json_protocol:
            def read_commands() -> None:
                for raw in sys.stdin:
                    commands.put(raw)
            threading.Thread(target=read_commands, daemon=True, name="novaui-preview-protocol-reader").start()
        try:
            while True:
                if args.json_protocol:
                    try:
                        raw = commands.get(timeout=0.25)
                    except queue.Empty:
                        continue
                    try:
                        message = parse_preview_command(raw.strip())
                        kind = message["type"]
                        if kind == "shutdown":
                            break
                        if kind == "refresh":
                            result = runtime.reload_preview()
                        elif kind == "select":
                            result = runtime.reload_preview(preview_name=message["name"])
                        elif kind == "theme":
                            runtime.set_theme(message["theme"])
                            result = None
                        elif kind == "viewport":
                            runtime.set_viewport(message["width"], message["height"])
                            result = None
                        elif kind == "reset":
                            result = runtime.reset_preview_state()
                        else:
                            result = None
                        response = {"version": 1, "type": kind, "ok": result.ok if result else True}
                        if result is not None:
                            response.update({"selected": result.selected, "error": result.error.to_dict() if result.error else None,
                                             "previews": [item.to_dict() for item in runtime.available_previews]})
                        if kind == "viewport":
                            response["viewport"] = {"width": runtime.viewport[0], "height": runtime.viewport[1]}
                        print("NOVAUI_PREVIEW " + json.dumps(response), flush=True)
                    except Exception as exc:  # noqa: BLE001 - reject malformed controls without ending preview.
                        print("NOVAUI_PREVIEW " + json.dumps({
                            "version": 1, "type": "error", "error": {"type": type(exc).__name__, "message": str(exc)}
                        }), flush=True)
                else:
                    idle.wait(1)
        except KeyboardInterrupt:
            pass
        return 0
    finally:
        runtime.close()


def _read_project_config(project_dir: Path) -> dict[str, object]:
    """Read the scalar subset of [tool.novaui] without a TOML dependency."""
    file = project_dir / "pyproject.toml"
    if not file.is_file():
        return {}
    section = False
    result: dict[str, object] = {}
    for number, raw in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line == "[tool.novaui]"
            continue
        if not section:
            continue
        if "=" not in line:
            raise ValueError(f"Invalid tool.novaui setting on pyproject.toml:{number}.")
        key, raw_value = (part.strip() for part in line.split("=", 1))
        if key not in {"entry", "mode", "host", "port"}:
            raise ValueError(f"Unknown tool.novaui setting {key!r} on line {number}.")
        try:
            value = ast.literal_eval(raw_value)
        except (ValueError, SyntaxError) as exc:
            raise ValueError(f"Invalid value for tool.novaui.{key} on line {number}.") from exc
        if key in {"entry", "mode", "host"} and not isinstance(value, str):
            raise ValueError(f"tool.novaui.{key} must be a string.")
        if key == "port" and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError("tool.novaui.port must be an integer.")
        result[key] = value
    return result


def _create(name: str, base: Path) -> None:
    if not _PROJECT_NAME.fullmatch(name) or keyword.iskeyword(name.replace("-", "_")):
        raise ValueError("Project name must start with a letter and contain only letters, digits, '_' or '-'.")
    target = base / name
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {target}")
    module = name.replace("-", "_")
    files = {
        "pyproject.toml": f'''[build-system]\nrequires = ["hatchling>=1.24"]\nbuild-backend = "hatchling.build"\n\n[project]\nname = "{name.lower().replace('_', '-')}"\nversion = "0.1.0"\nrequires-python = ">=3.10"\ndependencies = ["novaui>=0.1.0"]\n\n[project.optional-dependencies]\ndev = ["pytest>=8"]\ndesktop = ["pywebview>=5"]\n\n[tool.hatch.build.targets.wheel]\npackages = ["{module}"]\n\n[tool.novaui]\nentry = "app.py"\nmode = "web"\n''',
        "README.md": f"""# {name}\n\nInstall NovaUI (from its repository, use `python -m pip install -e /path/to/NovaUI-Starter`) and install this project with `python -m pip install -e '.[dev]'`.\n\nRun `novaui run` for web mode, or `novaui run --mode desktop` after installing `.[desktop]`.\nRun `novaui check` and `python -m pytest` for the starter checks.\n""",
        "app.py": f'''"""{name} NovaUI application."""\n\nimport novaui as ui\n\n\ndef MainPage():\n    return ui.Column(\n        ui.Text("Welcome to {name}"),\n        ui.Text("Edit app.py to build your interface."),\n        padding=24,\n        spacing=12,\n    )\n\n\nif __name__ == "__main__":\n    ui.app(MainPage(), title="{name}")\n''',
        f"{module}/__init__.py": '"""Reusable application components."""\n',
        "tests/test_app.py": '''import sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n\n\ndef test_main_page_serializes():\n    from app import MainPage\n\n    tree = MainPage().to_dict(lambda callback: "test-event")\n    assert tree["type"] == "column"\n    assert tree["children"][0]["text"] == "Welcome to {name}"\n'''.replace("{name}", name),
        "assets/.gitkeep": "",
    }
    for relative, content in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"Created {target}. Install NovaUI, then run `cd {name} && novaui run`.")


def _check(project_dir: Path) -> int:
    ignored = {".git", ".venv", "venv", "__pycache__", "dist", "build"}
    sources = [p for p in project_dir.rglob("*.py") if not any(part in ignored for part in p.parts)]
    for source in sources:
        try:
            compile(source.read_bytes(), str(source), "exec")
        except (OSError, SyntaxError) as exc:
            print(f"Python syntax failed: {source}: {exc}", file=sys.stderr)
            return 1
    print(f"Python syntax: passed ({len(sources)} files)")
    metadata = project_dir / "pyproject.toml"
    if metadata.is_file():
        content = metadata.read_text(encoding="utf-8")
        config_lines = content.splitlines()
        try:
            project_start = config_lines.index("[project]") + 1
        except ValueError:
            project_start = len(config_lines)
        project_lines: list[str] = []
        for line in config_lines[project_start:]:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]") and "=" not in stripped:
                break
            project_lines.append(line)
        project_section = "\n".join(project_lines)
        project_metadata: dict[str, str] = {}
        dynamic_fields: set[str] = set()
        for line in project_section.splitlines():
            key, separator, value_text = line.partition("=")
            metadata_key = key.strip()
            if separator and metadata_key in {"name", "version", "dynamic"}:
                try:
                    value = ast.literal_eval(value_text.strip())
                except (ValueError, SyntaxError):
                    continue
                if metadata_key in {"name", "version"} and isinstance(value, str) and value.strip():
                    project_metadata[metadata_key] = value
                elif metadata_key == "dynamic" and isinstance(value, list):
                    dynamic_fields = {field for field in value if isinstance(field, str)}
        if "name" not in project_metadata:
            print("Package metadata failed: pyproject.toml needs [project].name.", file=sys.stderr)
            return 1
        if "version" in project_metadata and "version" in dynamic_fields:
            print(
                "Package metadata failed: project version must be either static or dynamic, not both.",
                file=sys.stderr,
            )
            return 1
        if "version" not in project_metadata and "version" not in dynamic_fields:
            print(
                "Package metadata failed: pyproject.toml needs [project].version or "
                '"version" in [project].dynamic.',
                file=sys.stderr,
            )
            return 1
        print("Package metadata: passed (project name and static or dynamic version found)")
    else:
        print("Package metadata: skipped (no pyproject.toml)")
    try:
        import novaui
        if not novaui.__version__:
            raise RuntimeError("package version is empty")
    except Exception as exc:  # noqa: BLE001
        print(f"NovaUI import: failed ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 1
    print(f"NovaUI import: passed ({novaui.__version__})")
    tests = project_dir / "tests"
    if tests.is_dir():
        try:
            import pytest
        except ImportError:
            print("Tests: skipped (pytest is not installed; install `novaui[dev]`)")
        else:
            previous_dir = Path.cwd()
            try:
                os.chdir(project_dir)
                result = pytest.main(["-q"])
            finally:
                os.chdir(previous_dir)
            if result != pytest.ExitCode.OK:
                return int(result)
    else:
        print("Tests: skipped (no tests/ directory)")
    return 0


def _build(outdir: Path, project_dir: Path, *, debug: bool = False) -> int:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(outdir)],
            cwd=project_dir,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        print(f"Could not start Python build: {exc}", file=sys.stderr)
        return 1
    if result.returncode:
        print(f"Build failed (exit code {result.returncode}).", file=sys.stderr)
        details = result.stderr if debug else "\n".join(result.stderr.splitlines()[-6:])
        if details:
            print(details, file=sys.stderr)
        if "No module named build" in result.stderr:
            print("Install the build frontend with `python -m pip install 'novaui[build]'`.", file=sys.stderr)
    elif result.stdout:
        print(result.stdout, end="")
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    project_dir = Path.cwd().resolve()
    try:
        if args.command == "create":
            _create(args.name, project_dir)
            return 0
        if args.command == "check":
            return _check(project_dir)
        if args.command == "build":
            return _build(args.outdir, project_dir, debug=args.debug)
        if args.command == "preview":
            return _run_preview(args, project_dir)
        config = _read_project_config(project_dir)
        script = (args.script or Path(str(config.get("entry", "app.py")))).expanduser()
        script = (project_dir / script).resolve() if not script.is_absolute() else script.resolve()
        if not script.is_file():
            raise FileNotFoundError(f"application file not found: {script} (use `novaui run path/to/app.py`)")
        mode = args.mode or config.get("mode", "web")
        host = args.host or config.get("host", "127.0.0.1")
        port = args.port if args.port is not None else config.get("port", 0)
        if mode not in {"web", "desktop"}:
            raise ValueError("mode must be 'web' or 'desktop'.")
        if host not in {"127.0.0.1", "localhost"}:
            raise ValueError("Development server host must be loopback (127.0.0.1 or localhost).")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError("port must be an integer between 0 and 65535.")
        sys.argv = [str(script)]
        if args.debug:
            sys.argv.append("--debug")
        if mode == "desktop":
            sys.argv.append("--desktop")
        sys.argv.extend(["--host", str(host), "--port", str(port)])
        if args.no_browser or not args.open_browser:
            sys.argv.append("--no-browser")
        sys.path[0] = str(script.parent)
        with use_project_root(script.parent):
            runpy.run_path(str(script), run_name="__main__")
        return 0
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as exc:
        if args.debug:
            raise
        print(f"novaui: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        if args.debug:
            raise
        print(f"novaui: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
