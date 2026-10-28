"""Validated semantic theme tokens."""

from __future__ import annotations

import re
from dataclasses import dataclass

_COLOR = re.compile(
    r"^(?:#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})|"
    r"[A-Za-z]{1,24}|rgba?\([A-Za-z0-9.,%\s/+\-]+\)|hsla?\([A-Za-z0-9.,%\s/+\-]+\))$"
)
_LENGTH = re.compile(r"^(?:\d+(?:\.\d+)?|\.\d+)(?:px|rem|em|%)$|^0$", re.IGNORECASE)
_FONT_FAMILY = re.compile(r"^[A-Za-z0-9_ ,\-'\"]+$")


@dataclass(frozen=True)
class Theme:
    """Validated theme tokens applied to the shared frontend."""

    mode: str = "light"
    primary: str = "#4f46e5"
    radius: int | str = "22px"
    font_family: str = "Inter, ui-sans-serif, system-ui, sans-serif"
    name: str | None = None
    background: str | None = None
    surface: str | None = None
    foreground: str | None = None
    muted: str | None = None
    border: str | None = None
    primary_hover: str | None = None
    on_primary: str | None = None
    surface_raised: str | None = None
    primary_soft: str | None = None
    success: str | None = None
    warning: str | None = None
    danger: str | None = None
    info: str | None = None
    appearance: str = "solid"
    glass_blur: int | None = None
    glass_opacity: float | None = None

    def __post_init__(self) -> None:
        if self.name is not None and (
            not isinstance(self.name, str)
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", self.name)
        ):
            raise ValueError("Theme name must start with a letter and contain at most 64 letters, digits, or underscores.")
        if not isinstance(self.mode, str) or self.mode not in {"light", "dark"}:
            raise ValueError("Theme mode must be 'light' or 'dark'.")
        if not isinstance(self.appearance, str) or self.appearance not in {"solid", "glass"}:
            raise ValueError("Theme appearance must be 'solid' or 'glass'.")
        if (self.glass_blur is not None and
                (not isinstance(self.glass_blur, int) or isinstance(self.glass_blur, bool)
                 or not 0 <= self.glass_blur <= 64)):
            raise ValueError("Theme glass_blur must be an integer from 0 to 64 pixels.")
        if (self.glass_opacity is not None and
                (isinstance(self.glass_opacity, bool) or not isinstance(self.glass_opacity, (int, float))
                 or not 0.35 <= self.glass_opacity <= 0.95)):
            raise ValueError("Theme glass_opacity must be a number from 0.35 to 0.95.")
        if not isinstance(self.primary, str) or not _COLOR.fullmatch(self.primary.strip()):
            raise ValueError("Theme primary must be a CSS color name, hex, rgb, or hsl value.")
        radius = f"{self.radius}px" if isinstance(self.radius, int) and not isinstance(self.radius, bool) else self.radius
        if not isinstance(radius, str) or not _LENGTH.fullmatch(radius.strip()):
            raise ValueError("Theme radius must be a non-negative pixel integer or CSS length.")
        if isinstance(self.radius, int) and self.radius < 0:
            raise ValueError("Theme radius must be non-negative.")
        if not isinstance(self.font_family, str) or not _FONT_FAMILY.fullmatch(self.font_family.strip()):
            raise ValueError("Theme font_family contains unsupported characters.")
        color_tokens = (
            "background", "surface", "foreground", "muted", "border", "primary_hover", "on_primary",
            "surface_raised", "primary_soft", "success", "warning", "danger", "info",
        )
        for name in color_tokens:
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not _COLOR.fullmatch(value.strip())):
                raise ValueError(f"Theme {name} must be a CSS color name, hex, rgb, or hsl value, or None.")
        object.__setattr__(self, "primary", self.primary.strip())
        object.__setattr__(self, "radius", radius.strip())
        object.__setattr__(self, "font_family", self.font_family.strip())
        for name in color_tokens:
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, value.strip())

    def to_dict(self) -> dict[str, object]:
        variables: dict[str, str] = {
            "--primary": self.primary,
            "--radius": self.radius,
            "--font-family": self.font_family,
        }
        optional_tokens = {
            "background": "--bg",
            "surface": "--surface",
            "foreground": "--text",
            "muted": "--muted",
            "border": "--border",
            "primary_hover": "--primary-hover",
            "on_primary": "--on-primary",
            "surface_raised": "--surface-raised",
            "primary_soft": "--primary-soft",
            "success": "--success",
            "warning": "--warning",
            "danger": "--danger",
            "info": "--info",
        }
        for attribute, css_variable in optional_tokens.items():
            value = getattr(self, attribute)
            if value is not None:
                variables[css_variable] = value
        result: dict[str, object] = {
            "mode": self.mode,
            "variables": variables,
        }
        if self.appearance == "glass":
            result["appearance"] = self.appearance
            if self.glass_blur is not None:
                variables["--glass-blur"] = f"{self.glass_blur}px"
            if self.glass_opacity is not None:
                variables["--glass-opacity"] = f"{self.glass_opacity * 100:g}%"
        return result
