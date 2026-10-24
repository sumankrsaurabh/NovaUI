# Phase 11 application validation

These applications validate NovaUI against practical workflows. Run commands from the repository root in an environment where NovaUI is installed.

| Application | Command | Runtime | State/persistence |
|---|---|---|---|
| [NovaUI Studio](../examples/phase11_studio/README.md) | `python -m examples.phase11_studio.app` | Web | Selection and theme are in memory; sample catalogue is static |
| [NovaUI Admin](../examples/phase11_admin/README.md) | `python -m examples.phase11_admin.app` | Web | Sample records are in memory and reset on restart |
| [PyOffice Notes](../examples/phase11_pyoffice/README.md) | `python -m pip install -e '.[desktop]'` then `python -m examples.phase11_pyoffice.app` | Desktop | Explicit UTF-8 text file open/save; no automatic persistence |

The three projects share `examples/phase11_design.py` for themes and muted text color. They use NovaUI's renderer and public component APIs. The office prototype intentionally uses single-line inputs because the framework does not currently ship a multiline input, rich-text editor, or editable grid.

## Gap register

| ID / priority | App and workflow | Reproduction / expected | Actual behavior | Workaround | Proposed solution / regression coverage |
|---|---|---|---|---|---|
| G11-01 / P2 | Studio property inspector | Select a component and obtain its real constructor properties | Catalogue metadata is handwritten in the example; NovaUI exposes signatures but no stable property metadata contract | Curated catalogue is sufficient for this demo but can drift | Consider opt-in component metadata only after more components need it; test metadata against signatures |
| G11-02 / P2 | Studio copy sample in browser | Copy a displayed Python example | `ui.clipboard` is desktop-only; browser clipboard support is absent | Select and copy displayed text manually | Add an explicit browser clipboard bridge with origin/request validation and web tests |
| G11-03 / P2 | Admin visual reports | View a chart that updates with records | No chart component exists; report uses reactive text counts | Use summary counts | Evaluate one chart adapter in a separate milestone with data-update tests |
| G11-04 / P2 | PyOffice editing | Edit arbitrary-length multiline text and preserve file structure | Only single-line `Input` exists; this prototype is limited to 12 rows and canonical LF output | Keep documents within the documented limits | Add a properly labeled/accessible `TextArea` with value binding, then expand editor and test line-ending behavior |
| G11-05 / P2 | Admin asynchronous operations | Show progress during delayed work | The current callback/server flow is synchronous; no async loading lifecycle | Keep operations local and synchronous | Design background task lifecycle and cancellation before offering loading indicators |
| G11-06 / P3 | Admin notifications | Show transient success toast after actions | No toast component exists; form status is inline | Inline form status | Add a notification component only with timer/lifecycle cleanup support |

Priorities reflect this validation scope. There were no Phase 11 P0 findings; the pre-change framework suite passed. Desktop GUI behavior still requires manual testing on a graphical session with the OS webview backend installed.

## Tests

Application workflows are covered by `tests/test_phase11_apps.py`. Run the complete suite with:

```bash
python -m pytest -q
```

The tests serialize the apps and dispatch registered events without opening a browser or GUI. The text read/write helpers are exercised against temporary files. This does not substitute for manual cross-platform desktop testing.

## Performance scope

The `benchmarks/phase11.py` script measures Python-side operations only. On this Linux x86_64 environment (Python 3.14.4, Intel Core i3-7130U, 4 logical CPUs), the final 15-run medians were: Studio app construction plus disposal 0.379 ms; tree serialization 0.418 ms for Studio, 0.429 ms for Admin overview, 0.453 ms for Admin records, and 0.767 ms for PyOffice; registered event dispatch 0.010 ms. A direct state update had a 0.000739 ms median over 1,000 updates. A DataTable search plus full tree serialization over 1,000 records took 3.807 ms median, and 10,000 records took 20.501 ms; the current page serialized 20 visible rows. Fifteen Studio serializations peaked at 43.3 KiB of traced Python allocations.

These are small local runs, not browser paint, startup process, memory RSS, or desktop GUI benchmarks. The table still inspects and filters the entire in-memory dataset on each request and has no virtualization. Use `PYTHONPATH=. python benchmarks/phase11.py` to repeat; results will vary with hardware and system load.
