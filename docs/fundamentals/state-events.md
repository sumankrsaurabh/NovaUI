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
run in bounded server request workers. An `async def` event handler is awaited
before NovaUI returns the updated tree; it should not perform long-running
blocking work.

Use `ui.batch()` when one operation updates several states or changes one state
multiple times:

```python
with ui.batch():
    first_name.value = "Ada"
    last_name.value = "Lovelace"
```

State values update immediately, while subscriber notifications wait until the
outer batch exits. Each changed state notifies subscribers once with its latest
value. Nested batches join the outer batch, and notifications are flushed even
if the block exits with an exception.

`AsyncState` exposes `status` (`idle`, `loading`, `success`, or `error`),
`value`, and a sanitized `error` message for awaitable operations. Calling
`run()` cancels the previous operation; `cancel()` explicitly cancels the
current one. Cancellation propagates to the awaiting caller and stale
operations cannot replace the latest result.

`Input(value=state)` binds the field to `State[str]`. `on_change(value)` receives
the entered string and may return an error message or `None`. Inputs submit on
the browser change event, usually when focus leaves the field. `disabled` and
`read_only` block editing.

Events use one-shot opaque identifiers registered for the current tree. The
frontend cannot name arbitrary functions or send Python code. See
[security notes](../../SECURITY.md) for request limits and boundaries.

Failed event requests show an accessible browser diagnostic. The server returns
a safe generic error by default and logs the exception type without including
the exception message.
