"""A small native File menu backed by pywebview menu items."""
import novaui as ui


def about() -> None:
    print("NovaUI desktop sample — native menu action selected")


ui.desktop(
    ui.Column(ui.Text("Open the native File menu to see the About action."), padding=24),
    title="NovaUI Menu",
    menu=[ui.Menu("File", [ui.MenuItem("About NovaUI", about), ui.MenuSeparator(),
                            ui.MenuItem("Close", ui.window.close)])],
)
