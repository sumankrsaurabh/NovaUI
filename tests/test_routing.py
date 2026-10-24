import pytest

import novaui as ui


def test_router_matches_static_and_parameterized_paths_and_query_string():
    router = ui.Router(
        routes={
            "/": lambda: ui.Text("Home"),
            "/users/{user_id}": lambda user_id: ui.Text(f"User {user_id}"),
        }
    )
    app = ui.App(router)

    tree = app.serialize_tree("/users/42?tab=activity")["root"]
    assert tree["path"] == "/users/42?tab=activity"
    assert router.params == {"user_id": "42"}
    assert router.query_params == {"tab": ["activity"]}
    assert tree["children"][0]["text"] == "User 42"


def test_plain_component_app_ignores_browser_path_when_loading_tree():
    app = ui.App(ui.Text("Single page"))
    assert app.serialize_tree("/any/path?view=full")["root"]["text"] == "Single page"


def test_router_not_found_and_invalid_definitions():
    router = ui.Router(routes={"/": ui.Text("Home")}, not_found=ui.Text("Missing"))
    assert ui.App(router).serialize_tree("/missing")["root"]["children"][0]["text"] == "Missing"
    with pytest.raises(ValueError, match="duplicate route pattern"):
        ui.Router(routes={"/users/{id}": ui.Text("A"), "/users/{name}": ui.Text("B")})
    with pytest.raises(ValueError, match="route path"):
        ui.Router(routes={"users": ui.Text("Bad")})


def test_navigate_from_registered_callback_updates_router():
    router = ui.Router(
        routes={
            "/": lambda: ui.Button("Settings", on_click=lambda: ui.navigate("/settings")),
            "/settings": lambda: ui.Text("Settings page"),
        }
    )
    app = ui.App(router)
    button_event = app.serialize_tree()["root"]["children"][0]["event_id"]

    app.dispatch_event(button_event)
    tree = app.serialize_tree()["root"]
    assert tree["path"] == "/settings"
    assert tree["children"][0]["text"] == "Settings page"


def test_router_rejects_unsafe_paths_without_filesystem_access():
    app = ui.App(ui.Router(routes={"/": ui.Text("Home")}))
    for path in ("https://example.com/", "//example.com", "/../secret", "/%2e%2e/secret"):
        with pytest.raises(ValueError, match="navigation path"):
            app.serialize_tree(path)


def test_app_disposal_includes_components_on_routes_not_yet_opened():
    form = ui.Form(fields={"name": ui.Field()}, on_submit=lambda _values: None)
    router = ui.Router(routes={"/": ui.Text("Home"), "/form": form})
    app = ui.App(router)
    app.serialize_tree()
    field_state = form.fields["name"]._state
    app.dispose()
    assert field_state.is_disposed
