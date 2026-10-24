import pytest

import novaui as ui
from novaui.shortcuts import normalize_shortcut


@pytest.mark.parametrize(
    ("source", "expected"),
    [("Ctrl+S", "Ctrl+S"), ("Control+Shift+Z", "Ctrl+Shift+Z"),
     ("Mod+O", "Mod+O"), ("Alt+F4", "Alt+F4"), ("Meta+ArrowLeft", "Meta+ArrowLeft")],
)
def test_shortcuts_normalize_modifier_aliases(source, expected):
    assert normalize_shortcut(source) == expected


def test_shortcut_registration_validates_flags_and_names():
    registry = ui.ShortcutRegistry()
    with pytest.raises(TypeError, match="bools"):
        registry.register("Mod+S", lambda: None, allow_in_inputs=1)
    with pytest.raises(ValueError, match="Invalid shortcut"):
        registry.register("Mod+Run", lambda: None)
    with pytest.raises(TypeError, match="callable"):
        registry.register("Mod+S", None)
