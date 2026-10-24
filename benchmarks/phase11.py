"""Small local Python-side Phase 11 workflow benchmark (not a browser benchmark)."""

from __future__ import annotations

import platform
import statistics
import time
import tracemalloc
from collections.abc import Callable

import novaui as ui
from examples.phase11_admin.app import create_application
from examples.phase11_pyoffice.app import build_app as build_pyoffice
from examples.phase11_studio.app import build_app as build_studio


def median_ms(operation: Callable[[], object], repeats: int = 15) -> float:
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples)


def app_serialization(label: str, app: ui.App) -> tuple[str, float]:
    try:
        return label, median_ms(app.serialize_tree)
    finally:
        app.dispose()


def construct_and_dispose(factory: Callable[[], ui.App]) -> None:
    factory().dispose()


def table_filter(size: int) -> tuple[float, int]:
    records = [{"id": index, "name": f"Record {index:05d}", "group": f"Group {index % 10}"} for index in range(size)]
    app = ui.App(ui.DataTable(
        [ui.ColumnDef("id"), ui.ColumnDef("name"), ui.ColumnDef("group")],
        records,
        row_key="id",
        page_size=20,
    ))
    results = []
    try:
        for iteration in range(15):
            tree = app.serialize_tree()["root"]
            app.dispatch_event(tree["search_event_id"], "Record 009" if iteration % 2 == 0 else "Record 008")
            started = time.perf_counter()
            rendered = app.serialize_tree()["root"]
            results.append((time.perf_counter() - started) * 1000)
        return statistics.median(results), len(rendered["rows"])
    finally:
        app.dispose()


def main() -> None:
    print(f"Python: {platform.python_version()} | OS: {platform.platform()}")
    apps = [
        ("Studio tree serialization", build_studio()),
        ("Admin overview tree serialization", create_application()[0]),
        ("PyOffice tree serialization", build_pyoffice()),
    ]
    admin_records = create_application()
    admin_records[0].navigate("/records")
    apps.append(("Admin records route serialization", admin_records[0]))
    for label, elapsed in [app_serialization(label, app) for label, app in apps]:
        print(f"{label}: median {elapsed:.3f} ms (15 serializations)")
    startup = median_ms(lambda: construct_and_dispose(build_studio))
    print(f"Studio App construction + disposal: median {startup:.3f} ms (15 runs)")

    counter = ui.state(0)
    state_update = median_ms(lambda: counter.update(counter.value + 1), repeats=1000)
    counter.dispose()
    print(f"State update: median {state_update:.6f} ms (1000 updates)")

    calls = []
    event_app = ui.App(ui.Button("Run", on_click=lambda: calls.append(None)))
    dispatch_samples = []
    try:
        for _ in range(15):
            event_id = event_app.serialize_tree()["root"]["event_id"]
            started = time.perf_counter()
            event_app.dispatch_event(event_id)
            dispatch_samples.append((time.perf_counter() - started) * 1000)
    finally:
        event_app.dispose()
    print(f"Registered event dispatch: median {statistics.median(dispatch_samples):.3f} ms (15 callbacks)")

    for size in (1_000, 10_000):
        elapsed, visible = table_filter(size)
        print(f"DataTable search + render: {size:,} records, {visible} visible rows, median {elapsed:.3f} ms (15 runs)")

    tracemalloc.start()
    app = build_studio()
    for _ in range(15):
        app.serialize_tree()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    app.dispose()
    print(f"Studio repeated serialization peak traced allocation: {peak / 1024:.1f} KiB (15 renders)")


if __name__ == "__main__":
    main()
