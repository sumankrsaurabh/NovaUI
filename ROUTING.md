# Routing and application shells

`ui.Router` matches exact paths and `{parameter}` segments. Route factories receive named path parameters and return a component. Query strings are available through `router.query_params` as lists of values. `ui.navigate(path)` is available inside a registered event callback; it updates the server-side router and the browser history bridge uses `pushState`/`popstate` without a full-page reload.

```python
def user_page(user_id: str):
    return ui.Text(f"User {user_id}")

router = ui.Router(routes={
    "/": ui.Text("Home"),
    "/users/{user_id}": user_page,
}, not_found=ui.Text("No such page"))
ui.app(router)
```

Direct browser loads are supported: the HTTP server serves only its fixed frontend shell for non-API paths and asks the router to resolve the current path. It never joins a route path to a filesystem path. Unsafe paths and unknown API URLs are rejected. Navigation only works when the app root is a `Router` and from a NovaUI event callback.

`AppShell`, `Header`, `Sidebar`, `MainContent`, `Footer`, `NavigationItem`, and `Breadcrumbs` are small compositions of the existing layout components. `Tabs` renders one selected panel and provides accessible tab roles. Use CSS/theme properties to tune the shell; collapsible-sidebar state and automatic active-route discovery are not built in.

`Dialog(title, child, open=..., on_confirm=..., on_cancel=...)` keeps confirmation and cancellation on separate events. It never runs the confirm callback when opened. `Alert` and `Spinner` are available for inline status. A global imperative `ui.confirm()` and toast queue are not implemented.

Errors are intentionally generic to end users. Set `ui.app(..., debug=True)` during local development to include an exception class in event/render errors; exception text and submitted data are not returned. The current server is a local development server bound to `127.0.0.1`, not a production deployment architecture.
