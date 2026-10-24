# Contributing

NovaUI is an early-stage project. Public APIs may evolve before a stable 1.0 release. Avoid breaking documented behavior without tests, migration notes, and a roadmap update.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
```

Run checks from the repository root:

```bash
python -m ruff check novaui tests examples packaging
python -m pytest -q
node --check novaui/frontend/app.js
```

HTTP integration tests bind to loopback. Environments that prohibit local sockets cannot run those tests successfully.

## Change expectations

- Add tests for behavior and security-sensitive boundaries.
- Keep browser payloads structured and never execute client-provided code.
- Avoid logging application input or secrets.
- Document implemented APIs and limitations; do not mark planned work complete.
- Keep base dependencies minimal and optional integrations in extras.
- Include browser/desktop manual-test notes when a change needs a GUI.
- New components should include construction/serialization tests, a component-reference entry, and a runnable example where practical.

## Issues and pull requests

Bug reports should include the NovaUI version or commit, Python/OS details, a minimal reproducible example, expected behavior, and actual behavior. Remove passwords, tokens, personal data, and private files before sharing logs. Feature proposals should describe the user problem and a small API sketch; discuss larger changes before implementing them. Pull requests should state the behavior changed, tests and documentation updated, commands run, and any manual platform checks. Keep each change focused and do not claim untested platform support.

## API stability

NovaUI follows semantic versioning for released versions: patch releases are for compatible fixes, minor releases add backward-compatible features, and major releases may break APIs. Before 1.0, the public API is experimental unless a specific interface is marked stable in its docs; pre-1.0 minor releases may still revise experimental APIs. We aim to preserve documented APIs; incompatible changes require a reason, migration guidance, updated examples, and tests. Deprecations should be documented for at least one release before removal where practical.

## Security issues

See [SECURITY.md](SECURITY.md). Do not publish exploit details in an issue before contacting the maintainer privately.
