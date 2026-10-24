# State and events

`ui.state(value)` creates a Python `State`. Read `.value`, assign to it, or call
`.update(value)`. A computed `Text` tracks state reads and recomputes when those
values change:

```python
count = ui.state(0)
ui.Column(
    ui.Text(lambda: f"Count: {count.value}"),
    ui.Button("Add", on_click=lambda: count.update(count.value + 1)),
)
```

State changes are reflected when the browser requests a fresh component tree.
The current runtime does not push changes from background Python work. Callbacks
run synchronously in server request threads; asynchronous handlers are not
implemented.

`Input(value=state)` binds the field to `State[str]`. `on_change(value)` receives
the entered string and may return an error message or `None`. Inputs submit on
the browser change event, usually when focus leaves the field. `disabled` and
`read_only` block editing.

Events use one-shot opaque identifiers registered for the current tree. The
frontend cannot name arbitrary functions or send Python code. See
[security notes](../../SECURITY.md) for request limits and boundaries.
