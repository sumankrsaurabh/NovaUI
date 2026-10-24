from importlib.resources import files

import novaui as ui


def test_frontend_files_are_package_resources():
    frontend = files("novaui").joinpath("frontend")
    for filename in ("index.html", "app.js", "styles.css"):
        asset = frontend.joinpath(filename)
        assert asset.is_file()
        assert asset.read_bytes()


def test_minimal_application_serializes_without_optional_dependencies():
    app = ui.App(ui.Column(ui.Text("Installed package"), ui.Button("Run")))
    try:
        tree = app.serialize_tree()
        assert tree["root"]["children"][0]["text"] == "Installed package"
    finally:
        app.dispose()
