from __future__ import annotations

import sys
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import novaui as ui
from novaui.desktop import (
    DesktopWindow,
    WindowOptions,
    activate_window,
    build_native_menus,
)

app_module = import_module("novaui.app")


def test_window_options_validate_and_map_to_pywebview_names():
    options = WindowOptions(width=1000, height=700, min_width=500, min_height=300, fullscreen=True)
    assert options.to_backend_options() == {
        "width": 1000,
        "height": 700,
        "min_size": (500, 300),
        "resizable": True,
        "fullscreen": True,
        "frameless": False,
        "background_color": "#FFFFFF",
    }
    with pytest.raises(ValueError, match="positive integer"):
        WindowOptions(width=True)
    with pytest.raises(ValueError, match="cannot exceed"):
        WindowOptions(width=400, min_width=500)
    with pytest.raises(ValueError, match="#RRGGBB"):
        WindowOptions(background_color="red")


def test_window_facade_forwards_operations_and_file_dialog_results():
    raw = Mock()
    raw.create_file_dialog.side_effect = [("/tmp/document.txt",), None, ("/tmp/output.txt",)]
    backend = SimpleNamespace(FileDialog=SimpleNamespace(OPEN=10, SAVE=30))
    window = DesktopWindow(raw, backend)
    window.set_title("Editor")
    window.resize(800, 600)
    window.minimize()
    window.maximize()
    window.restore()
    window.toggle_fullscreen()
    assert window.open_file(file_types=["Text files (*.txt)"]) == "/tmp/document.txt"
    assert window.open_file() is None
    assert window.save_file(suggested_name="output.txt") == "/tmp/output.txt"
    raw.destroy.assert_not_called()
    assert raw.create_file_dialog.call_args_list[0].kwargs["file_types"] == ("Text files (*.txt)",)
    assert raw.create_file_dialog.call_args_list[2].kwargs["save_filename"] == "output.txt"
    window.close()
    raw.destroy.assert_called_once()


def test_file_dialog_facade_supports_legacy_pywebview_constants():
    raw = Mock()
    raw.create_file_dialog.return_value = None
    backend = SimpleNamespace(OPEN_DIALOG=10, SAVE_DIALOG=30)
    window = DesktopWindow(raw, backend)
    assert window.open_file() is None
    assert window.save_file() is None
    assert raw.create_file_dialog.call_args_list[0].args[0] == 10
    assert raw.create_file_dialog.call_args_list[1].args[0] == 30


def test_file_dialog_validation_and_web_only_errors():
    window = DesktopWindow(Mock(), SimpleNamespace(FileDialog=SimpleNamespace(OPEN=10, SAVE=30)))
    with pytest.raises(ValueError, match="File filters"):
        window.open_file(file_types=["../../*.txt"])
    with pytest.raises(ValueError, match="suggested_name"):
        window.save_file(suggested_name="bad\x00name")
    with pytest.raises(RuntimeError, match="desktop event callback"):
        ui.dialogs.open_file()
    with pytest.raises(RuntimeError, match="desktop event callback"):
        ui.clipboard.read_text()


def test_desktop_run_starts_window_and_always_closes_server(monkeypatch):
    calls = []

    class FakeServer:
        server_port = 34567

        def serve_forever(self):
            calls.append("serve")

        def shutdown(self):
            calls.append("shutdown")

        def server_close(self):
            calls.append("server_close")

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target
            calls.append(("thread", daemon))

        def start(self):
            self.target()

        def join(self, timeout=None):
            calls.append(("join", timeout))

    class Events:
        def __init__(self):
            self.handlers = []

        def __iadd__(self, handler):
            self.handlers.append(handler)
            return self

    raw_window = SimpleNamespace(events=SimpleNamespace(closing=Events()))
    backend = SimpleNamespace(
        FileDialog=SimpleNamespace(OPEN=10, SAVE=30),
        menu=SimpleNamespace(Menu=Mock(side_effect=lambda title, items: (title, items)),
                             MenuAction=Mock(side_effect=lambda title, callback: (title, callback)),
                             MenuSeparator=Mock(return_value="separator")),
        create_window=Mock(return_value=raw_window),
        start=Mock(side_effect=lambda **kwargs: calls.append(("start", kwargs))),
    )
    monkeypatch.setitem(sys.modules, "webview", backend)
    monkeypatch.setattr(app_module, "make_server", lambda _app: FakeServer())
    monkeypatch.setattr(app_module.threading, "Thread", FakeThread)
    application = ui.App(ui.Text("Desktop"), host="127.0.0.1", debug=True)
    application.on_close(lambda: False)
    application.run(desktop=True, window_options=WindowOptions(width=900, height=650))

    backend.create_window.assert_called_once()
    assert backend.create_window.call_args.args == ("NovaUI", "http://127.0.0.1:34567/")
    assert backend.create_window.call_args.kwargs["min_size"] == (200, 100)
    backend.start.assert_called_once_with(debug=True)
    assert calls.index("shutdown") < calls.index("server_close")
    assert application._disposed
    assert len(raw_window.events.closing.handlers) == 1
    assert raw_window.events.closing.handlers[0]() is False


def test_desktop_create_window_failure_still_shuts_server(monkeypatch):
    calls = []

    class FakeServer:
        server_port = 12345

        def serve_forever(self):
            pass

        def shutdown(self):
            calls.append("shutdown")

        def server_close(self):
            calls.append("close")

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target

        def start(self):
            pass

        def join(self, timeout=None):
            pass

    backend = SimpleNamespace(
        FileDialog=SimpleNamespace(OPEN=10, SAVE=30),
        menu=SimpleNamespace(Menu=Mock(), MenuAction=Mock(), MenuSeparator=Mock()),
        create_window=Mock(side_effect=RuntimeError("backend startup failed")),
        start=Mock(),
    )
    monkeypatch.setitem(sys.modules, "webview", backend)
    monkeypatch.setattr(app_module, "make_server", lambda _app: FakeServer())
    monkeypatch.setattr(app_module.threading, "Thread", FakeThread)
    with pytest.raises(RuntimeError, match="backend startup"):
        ui.App(ui.Text("Desktop")).run(desktop=True)
    assert calls == ["shutdown", "close"]


def test_desktop_requires_loopback_and_optional_dependency_message(monkeypatch):
    with pytest.raises(ValueError, match="loopback"):
        ui.App(ui.Text("No public bind"), host="0.0.0.0").run(desktop=True)

    real_import = __import__

    def no_webview(name, *args, **kwargs):
        if name == "webview":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", no_webview)
    with pytest.raises(RuntimeError, match=r'pip install "novaui\[desktop\]"'):
        ui.App(ui.Text("No backend")).run(desktop=True)


def test_close_callback_failure_is_logged_without_closing_window(caplog):
    application = ui.App(ui.Text("Desktop"))
    application.on_close(lambda: (_ for _ in ()).throw(RuntimeError("private close detail")))
    assert application._invoke_close_callback() is False
    assert "RuntimeError" in caplog.text
    assert "private close detail" not in caplog.text


def test_dialogs_use_the_active_desktop_window():
    raw = Mock()
    raw.create_file_dialog.return_value = ("/tmp/chosen.txt",)
    backend = SimpleNamespace(FileDialog=SimpleNamespace(OPEN=10, SAVE=30))
    window = DesktopWindow(raw, backend)
    with activate_window(window):
        assert ui.dialogs.open_file(title="Open", file_types=["Text files (*.txt)"]) == "/tmp/chosen.txt"
    assert raw.create_file_dialog.call_args.args == (10,)


def test_clipboard_uses_tk_text_only_api(monkeypatch):
    data = {"text": ""}

    class FakeRoot:
        def withdraw(self):
            pass

        def clipboard_clear(self):
            data["text"] = ""

        def clipboard_append(self, text):
            data["text"] = text

        def clipboard_get(self):
            return data["text"]

        def update(self):
            pass

        def destroy(self):
            pass

    monkeypatch.setitem(sys.modules, "tkinter", SimpleNamespace(Tk=FakeRoot))
    monkeypatch.setattr("novaui.clipboard.active_window", lambda: object())
    ui.clipboard.write_text("clipboard content")
    assert ui.clipboard.read_text() == "clipboard content"


def test_app_shortcuts_are_registered_replaced_unregistered_and_serialized():
    app = ui.App(ui.Text("Shortcuts"))
    calls = []
    app.shortcuts.register("Ctrl+S", lambda: calls.append("save"))
    with pytest.raises(ValueError, match="already registered"):
        app.shortcuts.register("Control+S", lambda: None)
    app.shortcuts.register("Ctrl+S", lambda: calls.append("new save"), replace=True)
    tree = app.serialize_tree()
    shortcut = tree["shortcuts"][0]
    app.dispatch_event(shortcut["event_id"])
    assert calls == ["new save"]
    app.shortcuts.set_enabled("Ctrl+S", False)
    assert app.serialize_tree()["shortcuts"] == []
    app.shortcuts.set_enabled("Ctrl+S", True)
    assert app.shortcuts.unregister("Ctrl+S")
    assert app.serialize_tree()["shortcuts"] == []
    with pytest.raises(ValueError, match="modifier"):
        app.shortcuts.register("S", lambda: None)


def test_shortcut_menu_and_close_callback_configuration_validation():
    with pytest.raises(ValueError, match="Menu title"):
        ui.Menu("", [])
    with pytest.raises(TypeError, match="MenuItem"):
        ui.Menu("File", ["Save"])
    with pytest.raises(TypeError, match="Menu item callback"):
        ui.MenuItem("Save", "not callable")
    with pytest.raises(TypeError, match="Close callback"):
        ui.App(ui.Text("x")).on_close("not callable")


def test_native_menu_builder_uses_explicit_items():
    calls = []
    backend = SimpleNamespace(menu=SimpleNamespace(
        Menu=lambda title, items: {"title": title, "items": items},
        MenuAction=lambda title, callback: (title, callback),
        MenuSeparator=lambda: "separator",
    ))
    native = build_native_menus(
        backend,
        [ui.Menu("File", [ui.MenuItem("Save", lambda: calls.append("save")), ui.MenuSeparator()])],
        lambda callback: callback(),
    )
    assert native[0]["title"] == "File"
    native[0]["items"][0][1]()
    assert calls == ["save"]


def test_desktop_convenience_api_validates_and_passes_options(monkeypatch):
    calls = []

    def fake_run(application, **kwargs):
        calls.append((application, kwargs))

    monkeypatch.setattr(ui.App, "run", fake_run)
    application = ui.desktop(
        ui.Text("Desktop"), title="Sample", width=900, height=700,
        min_width=500, min_height=350, resizable=False, debug=True,
    )
    assert calls[0][0] is application
    assert calls[0][1]["desktop"] is True
    assert calls[0][1]["window_options"].to_backend_options()["min_size"] == (500, 350)
    assert application.debug is True
