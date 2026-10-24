# PyOffice Notes prototype

A focused desktop plain-text workflow built from NovaUI's actual `Input`, layout, shortcut, and native file-dialog APIs. It opens and saves UTF-8 `.txt` documents selected explicitly by the user.

## Run

Install the optional desktop integration and a supported platform webview, then launch from the repository root:

```bash
python -m pip install -e '.[desktop]'
python -m examples.phase11_pyoffice.app
```

The application opens in desktop mode. `Mod+O` opens a file and `Mod+S` saves a file (`Mod` maps to Control on Linux/Windows and Command on macOS). The dialogs are desktop-only.

## Scope and limitations

This prototype supports at most 12 single-line rows, 2,000 characters per row, and 1 MB per UTF-8 file. Saving uses LF line endings and removes trailing empty rows. It is not a rich-text editor, spreadsheet, DOCX editor, or Excel-compatible application. NovaUI has no multiline editor or editable grid yet. No document is saved automatically; the user selects each open/save path.
