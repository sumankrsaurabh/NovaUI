from pathlib import Path

import pytest

import novaui as ui


def test_text_serializes():
    text = ui.Text("Hello", size=24, bold=True)
    data = text.to_dict(lambda callback: "unused")
    assert data["type"] == "text"
    assert data["text"] == "Hello"
    assert data["size"] == 24
    assert data["bold"] is True


def test_image_serializes_only_project_asset_paths():
    image = ui.Image("assets/logo.png", "NovaUI logo", width=240)
    data = image.to_dict(lambda callback: "unused")
    assert data["type"] == "image"
    assert data["src"] == "/assets/logo.png"
    assert data["alt"] == "NovaUI logo"
    assert data["width"] == 240
    with pytest.raises(ValueError, match="traverse"):
        ui.Image("assets/../../secret.txt", "secret").to_dict(lambda callback: "unused")


def test_callable_text_reads_current_state():
    value = ui.state(1)
    text = ui.Text(lambda: f"Value {value.value}")
    assert text.to_dict(lambda callback: "unused")["text"] == "Value 1"
    value.update(2)
    assert text.to_dict(lambda callback: "unused")["text"] == "Value 2"


def test_callable_text_caches_until_a_tracked_state_changes():
    value = ui.state(1)
    unrelated = ui.state(0)
    evaluations = []
    text = ui.Text(lambda: evaluations.append(value.value) or f"Value {value.value}")
    application = ui.App(text)

    assert application.serialize_tree()["root"]["text"] == "Value 1"
    assert application.serialize_tree()["root"]["text"] == "Value 1"
    unrelated.update(1)
    application.serialize_tree()
    assert evaluations == [1]

    value.update(2)
    assert application.serialize_tree()["root"]["text"] == "Value 2"
    assert evaluations == [1, 2]


def test_layout_serializes_children():
    data = ui.Column(ui.Text("A"), ui.Button("B"), spacing=10, width=320, height=180).to_dict(
        lambda callback: "event-1"
    )
    assert data["type"] == "column"
    assert len(data["children"]) == 2
    assert data["spacing"] == 10
    assert data["width"] == 320
    assert data["height"] == 180


def test_animated_component_serializes_child_and_validated_preset():
    data = ui.Animated(ui.Text("Welcome"), enter="fade_up", duration=180, easing="ease-out").to_dict(
        lambda callback: "unused"
    )
    assert data["type"] == "animated"
    assert data["enter"] == "fade_up"
    assert data["duration"] == 180
    assert data["children"][0]["text"] == "Welcome"


@pytest.mark.parametrize("kwargs", [
    {"enter": "wiggle"},
    {"duration": -1},
    {"duration": 2001},
    {"duration": True},
    {"easing": "steps(2)"},
])
def test_animated_rejects_unsupported_options(kwargs):
    with pytest.raises((TypeError, ValueError)):
        ui.Animated(ui.Text("Welcome"), **kwargs).to_dict(lambda callback: "unused")


def test_animated_requires_component_child():
    with pytest.raises(TypeError, match="child"):
        ui.Animated("not a component").to_dict(lambda callback: "unused")


def test_component_dimensions_are_validated():
    with pytest.raises(ValueError, match="non-negative"):
        ui.Card(ui.Text("A"), width=-1).to_dict(lambda callback: "unused")
    with pytest.raises(TypeError, match="integer"):
        ui.Button("Save", width="100%").to_dict(lambda callback: "unused")
    with pytest.raises(ValueError, match="variant"):
        ui.Button("Save", variant="danger").to_dict(lambda callback: "unused")
    with pytest.raises(ValueError, match="spacing"):
        ui.Column(ui.Text("A"), spacing=-1).to_dict(lambda callback: "unused")


def test_non_component_child_raises():
    with pytest.raises(TypeError):
        ui.Row("not a component").to_dict(lambda callback: "unused")


def test_button_registers_callback():
    seen = []
    button = ui.Button("Save", on_click=lambda: seen.append(True))
    events = {}
    def register(callback):
        events["callback"] = callback
        return "event-1"
    data = button.to_dict(register)
    assert data["event_id"] == "event-1"
    events["callback"]()
    assert seen == [True]


def test_input_binds_string_state_through_registered_event():
    value = ui.state("before")
    input_field = ui.Input(label="Name", value=value)
    callbacks = {}

    def register(callback):
        callbacks["input"] = callback
        return "input-event-1"

    data = input_field.to_dict(register)
    assert data["value"] == "before"
    assert data["event_id"] == "input-event-1"

    callbacks["input"]("after")
    assert value.value == "after"


def test_input_rejects_non_string_values():
    with pytest.raises(TypeError, match="string"):
        ui.Input(value=123).to_dict(lambda callback: "event-1")
    with pytest.raises(TypeError, match="string"):
        ui.Input(value=ui.state(123)).to_dict(lambda callback: "event-1")


def test_app_dispatches_input_values_to_registered_binding():
    value = ui.state("initial")
    application = ui.App(ui.Input(value=value))
    tree = application.serialize_tree()
    event_id = tree["root"]["event_id"]

    application.dispatch_event(event_id, "updated")

    assert value.value == "updated"


def test_app_rejects_values_for_non_input_events():
    application = ui.App(ui.Button("Save", on_click=lambda: None))
    event_id = application.serialize_tree()["root"]["event_id"]

    with pytest.raises(ValueError, match="does not accept a value"):
        application.dispatch_event(event_id, "unexpected")


def test_app_rejects_unknown_event_identifier():
    application = ui.App(ui.Text("Hello"))
    application.serialize_tree()

    with pytest.raises(ValueError, match="Unknown"):
        application.dispatch_event("event-from-browser")


def test_input_events_require_a_string_value():
    value = ui.state("initial")
    application = ui.App(ui.Input(value=value))
    event_id = application.serialize_tree()["root"]["event_id"]

    with pytest.raises(TypeError, match="string"):
        application.dispatch_event(event_id, 42)


def test_input_on_change_callback_receives_text():
    seen = []
    input_field = ui.Input(value="initial", on_change=seen.append)
    application = ui.App(input_field)
    event_id = application.serialize_tree()["root"]["event_id"]

    application.dispatch_event(event_id, "changed")

    assert seen == ["changed"]
    assert input_field.value == "changed"


def test_input_change_callback_can_set_and_clear_validation_error():
    value = ui.state("")
    input_field = ui.Input(value=value, on_change=lambda text: "Required" if not text else None)
    application = ui.App(input_field)
    event_id = application.serialize_tree()["root"]["event_id"]

    application.dispatch_event(event_id, "")
    assert application.serialize_tree()["root"]["error"] == "Required"

    event_id = application.serialize_tree()["root"]["event_id"]
    application.dispatch_event(event_id, "Nova")
    assert application.serialize_tree()["root"]["error"] is None


def test_input_read_only_or_disabled_has_no_event_id():
    value = ui.state("fixed")
    disabled = ui.Input(value=value, disabled=True).to_dict(lambda callback: "registered")
    read_only = ui.Input(value=value, read_only=True).to_dict(lambda callback: "registered")

    assert disabled["event_id"] is None
    assert read_only["event_id"] is None


def test_component_id_is_stable_across_serialization():
    component = ui.Text("stable")
    first = component.to_dict(lambda callback: "event")
    second = component.to_dict(lambda callback: "event")

    assert first["id"] == second["id"]
    assert ui.Text("another").to_dict(lambda callback: "event")["id"] != first["id"]


def test_app_accepts_supported_themes_and_rejects_unknown_theme():
    assert ui.App(ui.Text("light"), theme="light").serialize_tree()["theme"] == "light"
    assert ui.App(ui.Text("dark"), theme="dark").serialize_tree()["theme"] == "dark"
    with pytest.raises(ValueError, match="theme"):
        ui.App(ui.Text("invalid"), theme="blue")


def test_custom_theme_serializes_validated_css_variables():
    theme = ui.Theme(mode="dark", primary="#635BFF", radius=12, font_family="Inter, sans-serif")
    tree = ui.App(ui.Text("custom"), theme=theme).serialize_tree()

    assert tree["theme"] == {
        "mode": "dark",
        "variables": {
            "--primary": "#635BFF",
            "--radius": "12px",
            "--font-family": "Inter, sans-serif",
        },
    }
    with pytest.raises(ValueError, match="primary"):
        ui.Theme(primary="url(javascript:alert(1))")


def test_theme_supports_optional_semantic_color_tokens():
    theme = ui.Theme(
        mode="dark",
        primary="#3157D5",
        background="#10131A",
        surface="#1B202B",
        foreground="#F4F6FA",
        muted="#A6ADBB",
        border="#343B49",
        primary_hover="#5277EC",
    )
    variables = ui.App(ui.Text("tokens"), theme=theme).serialize_tree()["theme"]["variables"]
    assert variables["--bg"] == "#10131A"
    assert variables["--surface"] == "#1B202B"
    assert variables["--text"] == "#F4F6FA"
    assert variables["--muted"] == "#A6ADBB"
    assert variables["--border"] == "#343B49"
    assert variables["--primary-hover"] == "#5277EC"
    renderer = (Path(__file__).resolve().parents[1] / "novaui/frontend/app.js").read_text(encoding="utf-8")
    for token in ("--bg", "--surface", "--text", "--muted", "--border", "--primary-hover"):
        assert f'"{token}"' in renderer
    with pytest.raises(ValueError, match="surface"):
        ui.Theme(surface="url(javascript:alert(1))")


def test_component_instance_cannot_be_reused_in_one_tree():
    child = ui.Text("shared")
    application = ui.App(ui.Column(child, child))

    with pytest.raises(ValueError, match="only once"):
        application.serialize_tree()


def test_shared_layout_and_style_properties_serialize_as_safe_css_values():
    tree = ui.Column(
        ui.Text("Title", class_name="hero-title", style={"font-weight": 700, "color": "#123456"}),
        spacing=12,
        padding=24,
        max_width=1100,
        min_height="50vh",
        margin="0 auto",
        background="#ffffff",
        visible=True,
    ).to_dict(lambda callback: "unused")

    assert tree["styles"] == {
        "max-width": "1100px",
        "min-height": "50vh",
        "margin": "0 auto",
        "background": "#ffffff",
    }
    assert tree["visible"] is True
    assert tree["children"][0]["class_name"] == "hero-title"
    assert tree["children"][0]["styles"] == {"font-weight": "700", "color": "#123456"}


@pytest.mark.parametrize(
    "props",
    [
        {"visible": "yes"},
        {"class_name": "bad class; color:red"},
        {"max_width": "100%; display:none"},
        {"background": "url(javascript:alert(1))"},
        {"style": {"not-a-css-property": "value"}},
        {"style": {"color": "red;display:none"}},
    ],
)
def test_common_component_properties_reject_invalid_or_unsafe_values(props):
    component = ui.Container(ui.Text("safe"), **props)
    with pytest.raises((TypeError, ValueError)):
        component.to_dict(lambda callback: "unused")


def test_layout_components_serialize_nested_and_empty_children():
    tree = ui.Container(
        ui.Grid(ui.Text("A"), ui.Text("B"), columns=2, spacing=10),
        ui.Wrap(ui.Text("One"), ui.Text("Two")),
        ui.ScrollView(direction="horizontal", max_height=240),
        ui.Stack(ui.Text("overlay")),
        max_width=1100,
    ).to_dict(lambda callback: "unused")

    assert tree["type"] == "container"
    assert tree["children"][0]["type"] == "grid"
    assert tree["children"][0]["columns"] == "repeat(2, minmax(0, 1fr))"
    assert tree["children"][1]["type"] == "wrap"
    assert tree["children"][2]["direction"] == "horizontal"
    assert tree["children"][3]["type"] == "stack"
    assert ui.Grid().to_dict(lambda callback: "unused")["children"] == []


def test_grid_and_scroll_view_validate_configuration():
    with pytest.raises(ValueError, match="1 to 12"):
        ui.Grid(columns=0).to_dict(lambda callback: "unused")
    with pytest.raises(ValueError, match="direction"):
        ui.ScrollView(direction="diagonal").to_dict(lambda callback: "unused")
    with pytest.raises(ValueError, match="justify"):
        ui.Row(justify="left").to_dict(lambda callback: "unused")


def test_event_id_can_only_be_dispatched_once():
    seen = []
    application = ui.App(ui.Button("Save", on_click=lambda: seen.append("saved")))
    event_id = application.serialize_tree()["root"]["event_id"]

    application.dispatch_event(event_id)
    with pytest.raises(ValueError, match="already handled"):
        application.dispatch_event(event_id)

    assert seen == ["saved"]


def test_app_disposes_component_state_subscriptions():
    value = ui.state(1)
    application = ui.App(ui.Text(lambda: f"{value.value}"))
    application.serialize_tree()
    assert len(value._listeners) == 1

    application.dispose()

    assert value._listeners == []
    with pytest.raises(RuntimeError, match="disposed"):
        application.serialize_tree()


def test_failed_handler_keeps_current_event_available():
    attempts = []

    def handler():
        attempts.append("attempt")
        if len(attempts) == 1:
            raise RuntimeError("temporary failure")

    application = ui.App(ui.Button("Retry", on_click=handler))
    event_id = application.serialize_tree()["root"]["event_id"]

    with pytest.raises(RuntimeError, match="temporary failure"):
        application.dispatch_event(event_id)
    application.dispatch_event(event_id)

    assert attempts == ["attempt", "attempt"]
