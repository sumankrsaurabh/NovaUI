# Installation

NovaUI requires Python 3.10 or newer. The `novaui` project returned HTTP 404
from PyPI when checked on 2026-10-24, so no PyPI release is available yet.

From the repository root, create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

On Windows PowerShell, activate with:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

The base package has no runtime dependencies. The `dev` extra installs pytest,
Ruff, and `build`. Browser use needs no extra package. Desktop hosting is
optional:

```bash
python -m pip install -e '.[desktop]'
```

Linux desktop users also need a working graphical session and a pywebview GUI
backend. NovaUI documents GTK/WebKitGTK system packages and an optional Qt
extra in the [desktop guide](../desktop/runtime.md).

Install the current source checkout without development tools with
`python -m pip install .`. The public repository is
`https://github.com/sumankrsaurabh/NovaUI`; install its default branch with:

```bash
python -m pip install "git+https://github.com/sumankrsaurabh/NovaUI.git"
```

The PyPI command `python -m pip install novaui` will be available after the
first package release.

After installation, see [your first app](first-app.md). To create a project,
run `novaui create hello_app`; the CLI refuses to overwrite an existing path.
