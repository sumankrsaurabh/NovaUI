from __future__ import annotations

from importlib import import_module

import pytest

import novaui as ui

app_module = import_module("novaui.app")


class StatusBadge(ui.CustomComponent):
    def __init__(self, text: str, status: str = "success", **props):
        super().__init__(**props)
        if status not in {"success", "error"}:
            raise ValueError("unsupported status")
        self.text = text
        self.status = status

    def render(self):
        return ui.Text(self.text, color="#087443" if self.status == "success" else "#b42318")


def test_registered_custom_component_composes_builtin_renderer():
    extensions = ui.Extensions()
    extensions.register_component("StatusBadge", StatusBadge)
    application = ui.App(ui.Column(StatusBadge("Connected")), extensions=extensions)
    serialized = application.serialize_tree()["root"]
    assert serialized["children"][0]["text"] == "Connected"
    application.dispose()


def test_custom_component_requires_registration_in_each_app():
    application = ui.App(StatusBadge("Connected"))
    with pytest.raises(ValueError, match="not registered"):
        application.serialize_tree()
    application.dispose()


def test_custom_component_common_styles_use_existing_container_renderer():
    extensions = ui.Extensions()
    extensions.register_component("StatusBadge", StatusBadge)
    application = ui.App(StatusBadge("Connected", class_name="status-badge"), extensions=extensions)
    tree = application.serialize_tree()["root"]
    assert tree["type"] == "container"
    assert tree["class_name"] == "status-badge"
    assert tree["children"][0]["text"] == "Connected"
    application.dispose()


def test_component_registration_validates_names_and_duplicates():
    extensions = ui.Extensions()
    with pytest.raises(ValueError, match="name"):
        extensions.register_component("bad-name", StatusBadge)
    extensions.register_component("Badge", StatusBadge)
    with pytest.raises(ValueError, match="already registered"):
        extensions.register_component("Badge", StatusBadge)
    with pytest.raises(TypeError, match="subclass"):
        extensions.register_component("Other", ui.Text)


def test_named_themes_are_validated_and_applied():
    extensions = ui.Extensions()
    theme = ui.Theme(name="corporate", mode="dark", primary="#3157D5", radius="10px")
    extensions.register_theme(theme)
    app = ui.App(ui.Text("theme"), theme="corporate", extensions=extensions)
    assert app.serialize_tree()["theme"]["mode"] == "dark"
    with pytest.raises(ValueError, match="already registered"):
        extensions.register_theme(theme)
    with pytest.raises(ValueError, match="Unknown theme"):
        ui.App(ui.Text("theme"), theme="missing", extensions=extensions)


def test_plugin_setup_start_stop_and_services_are_app_scoped(monkeypatch):
    events = []

    class Plugin:
        name = "sample"
        min_novaui_version = "0.1.0"
        max_novaui_version_exclusive = "1.0.0"

        def setup(self, app):
            events.append("setup")
            app.register_service("sample", object())

        def on_app_start(self, app):
            events.append("start")

        def on_app_stop(self, app):
            events.append("stop")

    class Server:
        server_port = 8123

        def serve_forever(self):
            return None

        def shutdown(self):
            return None

        def server_close(self):
            return None

    monkeypatch.setattr(app_module, "make_server", lambda app: Server())
    extensions = ui.Extensions()
    extensions.use(Plugin())
    app = ui.App(ui.Text("plugin"), extensions=extensions)
    assert events == ["setup"]
    assert app.get_service("sample") is not None
    app.run(open_browser=False)
    assert events == ["setup", "start", "stop"]
    another_app = ui.App(ui.Text("isolated"))
    with pytest.raises(KeyError, match="No service"):
        another_app.get_service("sample")


def test_plugin_start_failure_stops_previously_started_plugins(monkeypatch):
    events = []

    class First:
        name = "first"

        def on_app_start(self, app):
            events.append("first-start")

        def on_app_stop(self, app):
            events.append("first-stop")

    class Failing:
        name = "failing"

        def on_app_start(self, app):
            events.append("failing-start")
            raise RuntimeError("startup failed")

        def on_app_stop(self, app):
            events.append("failing-stop")

    extensions = ui.Extensions()
    extensions.use(First())
    extensions.use(Failing())
    app = ui.App(ui.Text("plugin"), extensions=extensions)
    with pytest.raises(RuntimeError, match="startup failed"):
        app.run(open_browser=False)
    assert events == ["first-start", "failing-start", "failing-stop", "first-stop"]


def test_plugin_registration_and_compatibility_errors():
    class Plugin:
        name = "needs_future"
        min_novaui_version = "99.0.0"

        def setup(self, app):
            pass

    extensions = ui.Extensions()
    extensions.use(Plugin())
    with pytest.raises(RuntimeError, match="requires NovaUI"):
        ui.App(ui.Text("x"), extensions=extensions)
    with pytest.raises(ValueError, match="Plugin name"):
        extensions.use(type("Bad", (), {"name": "bad-name"})())


def test_plugin_duplicate_and_missing_optional_dependency_errors():
    class Plugin:
        name = "sample"
        optional_dependencies = ("novaui_test_dependency_that_does_not_exist",)

        def setup(self, app):
            return None

    extensions = ui.Extensions()
    extensions.use(Plugin())
    with pytest.raises(ValueError, match="already registered"):
        extensions.use(Plugin())
    with pytest.raises(RuntimeError, match="optional dependency"):
        ui.App(ui.Text("x"), extensions=extensions)
