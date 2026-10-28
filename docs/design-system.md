# NovaUI design system

NovaUI uses its own liquid-glass-inspired material over an indigo-and-neutral
visual foundation. It uses translucent layers, soft refraction cues, broad
rounded geometry, and restrained motion without copying external assets. The
base renderer does not download fonts or other style dependencies.

Use `Theme(appearance="glass")` to enable translucent surfaces across an
application, or use `Card(variant="glass")` / `Card(variant="glass-strong")`
for individual surfaces while leaving the rest of the app solid. A
`variant="solid"` card opts out of an app-wide glass theme.

## Defaults

| Token | Light | Dark | Use |
|---|---|---|---|
| Font | `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | same | UI typography; falls back to the installed system font |
| Primary | `#4F46E5` | `#A5A3FF` | Primary actions, active states, focus accent |
| Primary hover | `#4338CA` | `#BEBCFF` | Hover state |
| Background | `#F5F6FA` | `#10121B` | Application canvas |
| Surface | `#FFFFFF` | `#191C29` | Cards and controls |
| Raised surface | `#FFFFFF` | `#202435` | Elevated surfaces |
| Text | `#171A2B` | `#F2F3FA` | Main content |
| Muted text | `#697086` | `#A3A9BC` | Supporting content |
| Border | `#E3E6EF` | `#303548` | Dividers and control outlines |
| Card radius | `22px` | `22px` | Default card corners |
| Input radius | `14px` | `14px` | Fields and compact controls |
| Button radius | `999px` | `999px` | Capsule buttons |
| Overlay radius | `26px` | `26px` | Dialogs and large floating surfaces |

Glass combines translucent surfaces, fine borders, restrained highlights,
light surface shadows, and backdrop blur. Ordinary cards and controls rely on
their borders and tonal contrast; dialogs are the main elevated surface. The
page background adds subtle indigo, cyan, and
violet light fields so the translucent panels have visual depth. If backdrop
filtering is unavailable, panels use a more opaque fill for legibility.
The built-in material uses a 64% light fill and a 72% dark fill. Glass cards
use one restrained surface shadow; regular cards stay flat. `glass-strong`
uses a 62% fill, while `glass_opacity` customizes the app-wide material.

## Surface depth and icons

NovaUI uses borders and surface tones for most hierarchy. Cards and controls
stay close to the canvas; stronger elevation is reserved for dialogs. This
keeps a glass theme from making every card appear to float independently.

Use the bundled stroke icons to lead actions and navigation labels. They are
drawn with DOM SVG elements, so no icon package or remote asset is needed:

```python
import novaui as ui

ui.Row(
    ui.Button("Create project", icon="plus"),
    ui.Icon("search", label="Search"),
    ui.NavigationItem("Settings", "/settings", icon="settings"),
    spacing=12,
)
```

Primary buttons use a restrained brand gradient and soft color-matched glow.
Secondary icon buttons use a circular frosted surface with a gentle scale
response. Other controls stay quiet so these actions remain the visual focus.

`Icon` names are validated against the [component reference](../COMPONENTS.md).
Icons inside buttons are decorative because the visible button label supplies
the accessible name. Standalone icons are hidden from assistive technology
unless a `label` is provided.

Additional CSS tokens cover semantic status colors, a soft primary tint,
focus rings, compact/large/pill radius levels, a 4px-based spacing scale,
typography sizes and weights, control height, restrained shadow levels, motion
timings, and overlay z-index values. The built-in stylesheet also respects
`prefers-reduced-motion`.

## Theme overrides

Use `Theme` to override the supported colors, font, and common radius:

```python
import novaui as ui

brand = ui.Theme(
    name="brand",
    mode="light",
    appearance="glass",
    primary="#3157D5",
    primary_hover="#2446B5",
    on_primary="#FFFFFF",
    primary_soft="#EEF3FF",
    radius="14px",
    font_family="Inter, ui-sans-serif, system-ui, sans-serif",
    success="#16794B",
    warning="#995B00",
    danger="#B42332",
    info="#1769AA",
    glass_blur=32,
    glass_opacity=0.42,
)

ui.app(ui.Card(ui.Text("Branded surface")), theme=brand)
```

Theme color values are validated CSS colors. Supported optional fields are
`background`, `surface`, `surface_raised`, `foreground`, `muted`, `border`,
`primary_hover`, `on_primary`, `primary_soft`, `success`, `warning`, `danger`,
and `info`. Unspecified colors use the selected built-in light or dark palette.
`radius` controls default card rounding; an explicit `Card(radius=...)`
overrides it for that card. Inputs, buttons, and dialogs use their own shared
shape tokens so the hierarchy stays coherent.

`appearance` accepts `solid` or `glass`. `glass_blur` is an optional integer
from 0 to 64 pixels; `glass_opacity` is an optional number from 0.35 to 0.95.
Both are included in renderer tokens only for glass themes.

## Application CSS

Keep application-specific rules out of NovaUI's global stylesheet. Place CSS
under the project `assets/` directory, then pass its relative path:

```python
ui.App(root, stylesheets=("admin.css",))
```

The stylesheet is loaded after NovaUI's base styles and can use the same CSS
variables. Paths are limited to `.css` files under `assets/`; traversal and
absolute paths are rejected. The framework supports up to eight additional
stylesheets per app. This is a simple stylesheet hook, not a CSS bundler.

Apply `ui.Theme(appearance="glass")` to your app to see the glass design system
across its supported surfaces. Run `novaui run examples/themes.py` for a theme
switching demo and `novaui run examples/components.py` for a compact component
gallery.
