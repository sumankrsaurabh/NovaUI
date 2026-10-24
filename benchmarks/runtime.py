"""Small dependency-free Python runtime baseline; not a browser benchmark."""

from __future__ import annotations

import platform
import statistics
import time
import tracemalloc

import novaui as ui
from novaui.server import make_server

REPEATS = 7
ITERATIONS = 100


def median_ms_per_operation(operation, iterations: int = ITERATIONS) -> float:
    samples = []
    for _ in range(REPEATS):
        started = time.perf_counter_ns()
        for index in range(iterations):
            operation(index)
        samples.append((time.perf_counter_ns() - started) / iterations / 1_000_000)
    return statistics.median(samples)


def table_measurement(row_count: int) -> tuple[float, float]:
    data = [{"id": index, "name": f"Employee {index:05d}", "score": row_count - index} for index in range(row_count)]
    table = ui.DataTable(
        [ui.ColumnDef("id"), ui.ColumnDef("name"), ui.ColumnDef("score")],
        data,
        page_size=20,
    )
    app = ui.App(table)
    tree = app.serialize_tree()["root"]
    sort_event = tree["columns"][2]["sort_event_id"]
    app.dispatch_event(sort_event)
    serialization_ms = median_ms_per_operation(lambda _: app.serialize_tree(), iterations=10)
    tracemalloc.start()
    app.serialize_tree()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    app.dispose()
    return serialization_ms, peak / 1024


def main() -> None:
    children = tuple(ui.Text(f"Item {index}") for index in range(100))
    tree_app = ui.App(ui.Column(*children))
    state = ui.state(0)
    unsubscribe = state.subscribe(lambda _value: None)
    click_app = ui.App(ui.Button("Run", on_click=lambda: None))

    def dispatch(index: int) -> None:
        tree = click_app.serialize_tree()["root"]
        click_app.dispatch_event(tree["event_id"])

    def construct_app(_index: int) -> None:
        application = ui.App(ui.Column(*[ui.Text("x") for _ in range(100)]))
        application.dispose()

    print(f"Platform: {platform.platform()} | Python: {platform.python_version()} | machine: {platform.machine()}")
    print(f"Median across {REPEATS} runs; {ITERATIONS} operations per run where applicable")
    print(f"App construction with 100 Text children: {median_ms_per_operation(construct_app):.3f} ms/op")
    print(f"Tree serialization with 100 Text children: {median_ms_per_operation(lambda _: tree_app.serialize_tree()):.3f} ms/op")
    print(f"State update with one subscriber: {median_ms_per_operation(lambda i: state.update(i + 1)):.6f} ms/op")
    print(f"Event dispatch + new tree serialization: {median_ms_per_operation(dispatch, iterations=20):.3f} ms/op")

    def bind_and_close(_index: int) -> None:
        server = make_server(tree_app)
        server.server_close()

    print(f"HTTP server bind + close (no browser/thread): {median_ms_per_operation(bind_and_close, iterations=20):.3f} ms/op")
    for count in (100, 1_000, 5_000):
        duration, peak_kib = table_measurement(count)
        print(f"DataTable serialize, {count} rows / 3 columns / 20-row page: {duration:.3f} ms/op; traced peak {peak_kib:.1f} KiB")

    unsubscribe()
    tree_app.dispose()
    click_app.dispose()


if __name__ == "__main__":
    main()
