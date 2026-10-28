import json
import time
import urllib.error
import urllib.request

import pytest

import novaui as ui
from novaui.preview import PreviewRuntime, parse_preview_command


def write_source(tmp_path, text):
    source = tmp_path / "preview_app.py"
    source.write_text(text, encoding="utf-8")
    return source


def test_preview_decorator_forms_and_options():
    @ui.preview
    def First():
        return ui.Text("first")

    @ui.preview(name="Named", theme="dark", width=1200, height=800)
    def Second():
        return ui.Text("second")

    assert First.__novaui_preview__.name == "First"
    assert Second.__novaui_preview__.name == "Named"
    assert (Second.__novaui_preview__.width, Second.__novaui_preview__.height) == (1200, 800)
    assert Second.__novaui_preview__.identifier == "Second"


def test_explicit_preview_id_and_preview_state_scope():
    @ui.preview(id="stable-card", name="Card v1")
    def CardPreview():
        return ui.Text("card")

    assert CardPreview.__novaui_preview__.identifier == "stable-card"
    with pytest.raises(RuntimeError, match="inside a rendered"):
        ui.preview_state("count", 0)


def test_invalid_preview_signatures_are_rejected():
    with pytest.raises(TypeError, match="no parameters"):
        @ui.preview
        def Invalid(value):
            return ui.Text(value)

    with pytest.raises(TypeError, match="synchronous"):
        @ui.preview
        async def AsyncPreview():
            return ui.Text("x")


def test_discovery_does_not_call_preview_and_supports_multiple(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
called = []
@ui.preview
def One():
    called.append(True)
    return ui.Text("one")
@ui.preview(name="Two")
def two():
    called.append(True)
    return ui.Text("two")
''')
    runtime = PreviewRuntime(tmp_path)
    try:
        result = runtime.discover_previews(source)
        assert [item.name for item in result.previews] == ["One", "Two"]
        assert runtime._module.called == []
    finally:
        runtime.close()


def test_duplicate_names_are_diagnostic(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
@ui.preview(name="same")
def One(): return ui.Text("one")
@ui.preview(name="same")
def Two(): return ui.Text("two")
''')
    result = ui.discover_previews(source, workspace=tmp_path)
    assert result.error.error_type == "ValueError"
    assert "Duplicate preview name" in result.error.message


def test_duplicate_ids_are_diagnostic(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
@ui.preview(id="same", name="One")
def One(): return ui.Text("one")
@ui.preview(id="same", name="Two")
def Two(): return ui.Text("two")
''')
    result = ui.discover_previews(source, workspace=tmp_path)
    assert result.error is not None
    assert "Duplicate preview id" in result.error.message


def test_runtime_renders_and_dispatches_real_button_event(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
@ui.preview
def CounterPreview():
    count = ui.state(0)
    return ui.Column(ui.Text(lambda: f"Count: {count.value}"),
                     ui.Button("+", on_click=lambda: count.update(count.value + 1)))
''')
    runtime = PreviewRuntime(tmp_path)
    try:
        result = runtime.render_preview(source)
        assert result.ok
        assert result.tree["root"]["children"][0]["text"] == "Count: 0"
        event_id = result.tree["root"]["children"][1]["event_id"]
        updated = runtime.dispatch_event(event_id)
        assert updated["root"]["children"][0]["text"] == "Count: 1"
    finally:
        runtime.close()


def test_syntax_error_keeps_successful_tree_and_recovers(tmp_path):
    source = write_source(tmp_path, 'import novaui as ui\n@ui.preview\ndef Preview(): return ui.Text("ok")\n')
    runtime = PreviewRuntime(tmp_path)
    try:
        first = runtime.render_preview(source)
        source.write_text("import novaui as ui\n@ui.preview\ndef Preview(:\n", encoding="utf-8")
        failed = runtime.reload_preview()
        assert not failed.ok and failed.error.error_type == "SyntaxError"
        assert failed.tree == first.tree
        source.write_text('import novaui as ui\n@ui.preview\ndef Preview(): return ui.Text("recovered")\n', encoding="utf-8")
        recovered = runtime.reload_preview()
        assert recovered.ok
        assert recovered.tree["root"]["text"] == "recovered"
    finally:
        runtime.close()


def test_reload_disposes_old_components(tmp_path):
    source = write_source(tmp_path, 'import novaui as ui\n@ui.preview\ndef Preview(): return ui.Text("old")\n')
    runtime = PreviewRuntime(tmp_path)
    try:
        runtime.render_preview(source)
        old_components = list(runtime.app._components.values())
        source.write_text(source.read_text().replace("old", "new"), encoding="utf-8")
        assert runtime.reload_preview().ok
        assert all(component._disposed for component in old_components if hasattr(component, "_disposed"))
    finally:
        runtime.close()


def test_custom_component_classes_refresh_with_module_reload(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
class Greeting(ui.CustomComponent):
    def render(self): return ui.Text("first")
@ui.preview
def Preview(): return Greeting()
''')
    runtime = PreviewRuntime(tmp_path)
    try:
        first = runtime.render_preview(source)
        assert first.ok and first.tree["root"]["text"] == "first"
        source.write_text(source.read_text().replace('"first"', '"second"'), encoding="utf-8")
        second = runtime.reload_preview()
        assert second.ok and second.tree["root"]["text"] == "second"
    finally:
        runtime.close()


def test_workspace_escape_and_missing_source(tmp_path):
    runtime = PreviewRuntime(tmp_path)
    try:
        result = runtime.discover_previews(tmp_path.parent / "outside.py")
        assert result.error is not None
        missing = runtime.discover_previews("missing.py")
        assert missing.error.error_type == "FileNotFoundError"
    finally:
        runtime.close()


def test_protocol_rejects_invalid_payloads_and_boolean_version():
    valid = parse_preview_command(json.dumps({"version": 1, "type": "viewport", "width": 800, "height": 600}))
    assert valid["type"] == "viewport"
    invalid = (
        "{}", '{"version":true,"type":"shutdown"}', '{"version":1,"type":"exec"}',
        '{"version":1,"type":"theme","theme":"system"}',
        '{"version":1,"type":"refresh","extra":1}',
    )
    for raw in invalid:
        with pytest.raises(ValueError):
            parse_preview_command(raw)


def test_preview_server_requires_session_token(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
@ui.preview
def Preview():
    count = ui.state(0)
    return ui.Column(ui.Text(lambda: f"Count: {count.value}"),
                     ui.Button("+", on_click=lambda: count.update(count.value + 1)))
''')
    runtime = PreviewRuntime(tmp_path)
    try:
        assert runtime.render_preview(source).ok
        url = runtime.start_server()
        endpoint = url.split("#", 1)[0] + "api/tree"
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(endpoint)
        assert error.value.code == 403
        request = urllib.request.Request(
            endpoint,
            headers={"X-NovaUI-Preview-Token": runtime._session_token, "X-NovaUI-Request": "tree"},
        )
        with urllib.request.urlopen(request) as response:
            assert response.status == 200
            tree = json.loads(response.read())
        assert tree["root"]["children"][0]["text"] == "Count: 0"
        origin = endpoint.split("/api/", 1)[0]
        event_request = urllib.request.Request(
            origin + "/api/event",
            data=json.dumps({"event_id": tree["root"]["children"][1]["event_id"]}).encode(),
            headers={
                "Content-Type": "application/json",
                "Origin": origin,
                "X-NovaUI-Preview-Token": runtime._session_token,
            },
            method="POST",
        )
        with urllib.request.urlopen(event_request) as response:
            updated = json.loads(response.read())
        assert updated["root"]["children"][0]["text"] == "Count: 1"
    finally:
        runtime.close()


def test_watcher_debounces_source_updates(tmp_path):
    source = write_source(tmp_path, 'import novaui as ui\n@ui.preview\ndef Preview(): return ui.Text("old")\n')
    runtime = PreviewRuntime(tmp_path)
    updates = []
    try:
        runtime.render_preview(source)
        runtime.on_change = updates.append
        runtime.start_watching(interval=0.05, debounce=0.05)
        source.write_text(source.read_text().replace("old", "new"), encoding="utf-8")
        deadline = time.monotonic() + 3
        while not updates and time.monotonic() < deadline:
            time.sleep(0.03)
        assert updates and updates[-1].ok
        assert updates[-1].tree["root"]["text"] == "new"
    finally:
        runtime.close()


def test_reload_preserves_explicit_state_and_reset_clears_it(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
@ui.preview
def Counter():
    count = ui.preview_state("count", 0)
    return ui.Column(ui.Text(lambda: f"Count: {count.value}"), ui.Button("+", on_click=lambda: count.update(count.value + 1)))
''')
    runtime = PreviewRuntime(tmp_path)
    try:
        first = runtime.render_preview(source)
        event_id = first.tree["root"]["children"][1]["event_id"]
        updated = runtime.dispatch_event(event_id)
        assert updated["root"]["children"][0]["text"] == "Count: 1"
        source.write_text(source.read_text().replace('"count", 0', '"count", 10'), encoding="utf-8")
        reloaded = runtime.reload_preview()
        assert reloaded.ok
        assert reloaded.tree["root"]["children"][0]["text"] == "Count: 1"
        reset = runtime.reset_preview_state()
        assert reset.ok
        assert reset.tree["root"]["children"][0]["text"] == "Count: 10"
    finally:
        runtime.close()


def test_preview_states_are_isolated_and_removed_previews_refresh_discovery(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
@ui.preview(id="first", name="First")
def First():
    count = ui.preview_state("count", 0)
    return ui.Column(ui.Text(lambda: f"First {count.value}"), ui.Button("+", on_click=lambda: count.update(count.value + 1)))
@ui.preview(id="second", name="Second")
def Second():
    count = ui.preview_state("count", 100)
    return ui.Text(f"Second {count.value}")
''')
    runtime = PreviewRuntime(tmp_path)
    try:
        first = runtime.render_preview(source, "First")
        event_id = first.tree["root"]["children"][1]["event_id"]
        runtime.dispatch_event(event_id)
        second = runtime.reload_preview(preview_name="Second")
        assert second.ok and second.tree["root"]["text"] == "Second 100"
        source.write_text(source.read_text().split('@ui.preview(id="second"')[0], encoding="utf-8")
        fallback = runtime.reload_preview()
        assert fallback.ok and fallback.selected == "First"
        assert [item.name for item in fallback.previews] == ["First"]
    finally:
        runtime.close()


def test_protocol_supports_state_reset():
    assert parse_preview_command('{"version":1,"type":"reset"}') == {"version": 1, "type": "reset"}


def test_stable_id_preserves_selection_when_display_name_changes(tmp_path):
    source = write_source(tmp_path, '''
import novaui as ui
@ui.preview(id="stable", name="Before")
def View(): return ui.Text("preview")
''')
    runtime = PreviewRuntime(tmp_path)
    try:
        assert runtime.render_preview(source).ok
        source.write_text(source.read_text().replace('name="Before"', 'name="After"'), encoding="utf-8")
        result = runtime.reload_preview()
        assert result.ok and result.selected == "After"
        assert [preview.name for preview in result.previews] == ["After"]
    finally:
        runtime.close()
