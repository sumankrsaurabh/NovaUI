# Forms and routing

## Forms

Use `Field` for a string value and validation rules, then pass fields and a
synchronous callback to `Form`:

```python
email = ui.Field(label="Email", input_type="email", required=True)

def submit(values: dict[str, str]) -> None:
    print("Received a form submission")

form = ui.Form(fields={"email": email}, on_submit=submit)
ui.app(form)
```

Fields support required, length, number-range, and custom validation. A form
tracks errors and dirty values and supports reset/revalidation. Values are
strings. Validation in the UI is not a security boundary; validate sensitive
values again in trusted application logic. Full API details are in the
[forms guide](../../FORMS.md).

## Routing

```python
def user_page(user_id: str) -> ui.Component:
    return ui.Text(f"User {user_id}")

router = ui.Router(routes={
    "/": ui.Text("Home"),
    "/users/{user_id}": user_page,
}, not_found=ui.Text("Page not found"))
ui.app(router)
```

`ui.navigate(path)` is intended for a registered event callback. The browser
uses its History API for back/forward navigation. Route patterns support
single-segment parameters; query values are available from `router.query_params`.
See the [routing guide](../../ROUTING.md).
