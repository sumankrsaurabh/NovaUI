"""Generate the constructor-signature appendix in COMPONENTS.md."""

from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import novaui as ui

START = "<!-- BEGIN GENERATED COMPONENT CONSTRUCTORS -->"
END = "<!-- END GENERATED COMPONENT CONSTRUCTORS -->"
REFERENCE = ROOT / "COMPONENTS.md"


def generated_section() -> str:
    components = sorted(
        (name, value)
        for name, value in vars(ui).items()
        if isinstance(value, type)
        and value is not ui.Component
        and issubclass(value, ui.Component)
        and not name.startswith("_")
    )
    lines = [
        START,
        "## Constructor signatures",
        "",
        "Generated from the exported component constructors. Refresh with `python scripts/generate_component_reference.py`.",
        "",
    ]
    for name, component_type in components:
        lines.append(f"- `{name}{inspect.signature(component_type)}`")
    lines.extend(["", END])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the generated section is stale")
    args = parser.parse_args()
    content = REFERENCE.read_text(encoding="utf-8")
    if content.count(START) != 1 or content.count(END) != 1:
        parser.error("COMPONENTS.md must contain exactly one pair of generated-section markers.")
    before, remainder = content.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = before.rstrip() + "\n\n" + generated_section() + after
    if args.check:
        if updated != content:
            print("COMPONENTS.md constructor signatures are stale.", file=sys.stderr)
            return 1
        return 0
    REFERENCE.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
