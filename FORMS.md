# Forms

`ui.Field` keeps a string value and its validation rules; `ui.Form` renders fields, collects browser input through generated event IDs, validates on the Python side, and invokes a callback with a copy of the submitted values. Callbacks may be synchronous or `async def`; NovaUI awaits asynchronous submissions before returning the updated tree.

```python
email = ui.Field(label="Email", input_type="email", required=True)
password = ui.Field(label="Password", input_type="password", required=True, min_length=8)

def sign_in(values: dict[str, str]) -> None:
    # Validate credentials and authorize against trusted application services here.
    print("Sign in requested for", values["email"])

form = ui.Form(fields={"email": email, "password": password}, on_submit=sign_in)
ui.app(form)
```

Supported `Field` types are `text`, `email`, `password`, `number`, and `date`.
For standalone controls, `TextArea`, `Checkbox`, `Switch`, `Select`, `Slider`,
and `DatePicker` provide multiline, boolean, enumerated, numeric-range, and
date values with server-validated event payloads.
`Form` currently owns string `Field` values; use these standalone components
when a form needs a non-string value. Fields support `required`, `min_length`,
`max_length`, numeric `min_value`/`max_value`, a synchronous
`validator(value) -> str | None`, and `async_validator(value)` returning an
awaitable error string or `None`, plus `disabled` and `placeholder`. Async
validation runs on change and before submission; a newer value, reset, or
component disposal cancels stale validation. Validator exceptions produce a
generic user-facing message and a type-only log entry. `Form` exposes
`values`, `errors`, `dirty_fields`, `revalidate()`, `reset()`, `submit_label`,
`reset_label`, and external `disabled`/`loading` flags. The `validators` mapping
can validate a field against all submitted values; each value is a synchronous
callback receiving the complete values mapping and returning a message or
`None`. Cross-field validators remain synchronous. Validation failures are
summarized accessibly before the fields. A
successful callback may return a status string; callback exceptions produce a
generic status and a safe log entry. Async callback results are awaited, but a
live loading message is not streamed while the server waits.

Custom validators run in Python:

`NumberField` is a validated numeric `Input` convenience constructor.
`SearchField` supplies a clear action and submits the current string to its
callback. `Form(validators={field_name: callback})` supports cross-field checks;
the callback receives the full values mapping and returns an error string or
`None`. Submission callbacks may be async and are awaited in the event request.

```python
def validate_handle(value: str) -> str | None:
    return "Use at least one letter." if not any(ch.isalpha() for ch in value) else None

handle = ui.Field(required=True, validator=validate_handle)
```

Cross-field validation can target a field and inspect sibling values:

```python
form = ui.Form(
    fields={"password": ui.Field(), "confirm": ui.Field(label="Confirm password")},
    on_submit=save_account,
    validators={
        "confirm": lambda values: (
            "Passwords do not match." if values["password"] != values["confirm"] else None
        ),
    },
)
```

The browser's native constraints are only a usability aid. Form checks in this local UI process are not a security boundary. Repeat sensitive validation and authorization in trusted server-side business logic. Password values are not stored in browser storage or logged by NovaUI, but the current event bridge sends form values to the Python process over the local HTTP connection.
