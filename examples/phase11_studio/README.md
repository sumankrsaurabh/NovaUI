# NovaUI Studio

NovaUI Studio is a developer playground for a fixed catalogue of implemented components. It exercises component selection, live name/category search, previews, constructor-signature inspection, theme switching, and example display. Constructor signatures are derived from the public Python constructors; descriptions and safe preview/code samples are curated by the example. It never evaluates code entered by a user.

## Run

From the repository root, after installing NovaUI in the current environment:

```bash
python -m examples.phase11_studio.app
```

The command opens a browser. Add `--no-browser` to leave it running without opening one. Desktop clipboard access is available when launched with the optional desktop setup; in a browser, users can select the displayed sample text manually.

## Limitations

The catalogue is intentionally limited to the components with working renderer support. Examples are displayed as text and are not evaluated. Documentation paths are references; the application does not host the Markdown source. The showcase uses the same stylesheet as NovaUI apps, with a responsive Studio layout.
