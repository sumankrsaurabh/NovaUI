# NovaUI Admin

A local administration dashboard demonstrating NovaUI routing, shell layouts, forms, searchable/sortable/filterable/paginated data tables, confirmation dialogs, reports, and app-level theme changes.

## Run

```bash
python -m examples.phase11_admin.app
```

Use `--no-browser` to suppress browser launch. Routes are `/`, `/records`, `/entry`, `/reports`, and `/settings`; unknown routes render an in-app not-found page.

## Data and limitations

Seven sample records live in a Python `State` object. Add/remove operations update the current process only and reset on restart. Reports are reactive text summaries; charts, toast notifications, editable grids, and persistent settings are not implemented. Form errors and route not-found behavior provide error states. The runtime is synchronous, so this app does not claim an asynchronous loading workflow.
