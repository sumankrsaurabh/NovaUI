# Forms

`ui.Field` keeps a string value and its validation rules; `ui.Form` renders fields, collects browser input through generated event IDs, validates on the Python side, and invokes a synchronous callback with a copy of the submitted values.

```python
email = ui.Field(label="Email", input_type="email", required=True)
password = ui.Field(label="Password", input_type="password", required=True, min_length=8)

def sign_in(values: dict[str, str]) -> None:
    # Validate credentials and authorize against trusted application services here.
    print("Sign in requested for", values["email"])

form = ui.Form(fields={"email": email, "password": password}, on_submit=sign_in)
ui.app(form)
```

Supported field types are `text`, `email`, `password`, `number`, and `date`. Fields support `required`, `min_length`, `max_length`, numeric `min_value`/`max_value`, a `validator(value) -> str | None`, `disabled`, and `placeholder`. `Form` exposes `values`, `errors`, `dirty_fields`, `revalidate()`, `reset()`, `submit_label`, `reset_label`, and external `disabled`/`loading` flags. A successful callback may return a status string; callback exceptions produce a generic status and a safe log entry. Because callbacks are synchronous, the browser cannot show a transient loading indicator while a callback is running. Async callbacks are not supported yet.

Custom validators run in Python:

```python
def validate_handle(value: str) -> str | None:
    return "Use at least one letter." if not any(ch.isalpha() for ch in value) else None

handle = ui.Field(required=True, validator=validate_handle)
```

The browser's native constraints are only a usability aid. Form checks in this local UI process are not a security boundary. Repeat sensitive validation and authorization in trusted server-side business logic. Password values are not stored in browser storage or logged by NovaUI, but the current event bridge sends form values to the Python process over the local HTTP connection.
