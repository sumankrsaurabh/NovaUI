# NovaUI examples

These small applications use the current public API. From the repository root,
run one with `python -m novaui run examples/<file>.py` or `novaui run
examples/<file>.py`. Browser mode uses a loopback server. Add `--mode desktop`
to the CLI command for the desktop example after installing the desktop extra
and a platform webview.

| Example | What it demonstrates | Run |
| --- | --- | --- |
| Counter | Reactive state and a live preview declaration | `novaui run examples/counter.py` |
| Forms | Python validation and submission status | `novaui run examples/forms.py` |
| Dashboard | Responsive `Scaffold`, route-aware navigation, SVG charts, routes, and a searchable data table | `novaui run examples/dashboard.py` |
| Themes | Glass styling and changing the active theme | `novaui run examples/themes.py` |
| Components | Buttons, cards, badges, progress, skeleton, and layout | `novaui run examples/components.py` |
| Desktop | Native file picker and desktop window | `novaui run examples/desktop.py --mode desktop` |

For IDE preview, open `counter.py` and run **NovaUI: Open Live Preview** in
the VS Code extension. Preview functions must be top-level and take no
arguments. The runtime executes workspace Python as trusted code.

The examples use only NovaUI's implemented components. Charts currently cover
line, bar, area, and doughnut views using browser-native SVG. Editable grids,
rich-text editing, and upload widgets are not included yet.
