import pytest

import novaui as ui
from novaui import cli


def test_cli_run_selects_mode_and_loopback_options(tmp_path, monkeypatch):
    application_file = tmp_path / "app.py"
    application_file.write_text("# test application\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(cli.runpy, "run_path", lambda *args, **kwargs: calls.append((args, kwargs)))

    assert cli.main(["run", str(application_file), "--mode", "desktop", "--port", "9000"]) == 0
    assert calls[0][0][0] == str(application_file)
    assert cli.sys.argv == [str(application_file), "--desktop", "--host", "127.0.0.1", "--port", "9000", "--no-browser"]

    assert cli.main(["run", str(application_file), "--mode", "web", "--host", "localhost"]) == 0
    assert cli.sys.argv == [str(application_file), "--host", "localhost", "--port", "0", "--no-browser"]


def test_cli_reads_project_config_and_command_line_takes_precedence(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.novaui]\nentry = "src/main.py"\nmode = "web"\nhost = "127.0.0.1"\nport = 8181\n',
        encoding="utf-8",
    )
    entry = tmp_path / "src" / "main.py"
    entry.parent.mkdir()
    entry.write_text("# application\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.runpy, "run_path", lambda *args, **kwargs: None)

    assert cli.main(["run", "--port", "9090"]) == 0
    assert cli.sys.argv == [str(entry), "--host", "127.0.0.1", "--port", "9090", "--no-browser"]


def test_direct_script_assets_resolve_from_entrypoint_when_cwd_differs(tmp_path, monkeypatch):
    project = tmp_path / "application"
    project.mkdir()
    entry = project / "app.py"
    entry.write_text("# entrypoint\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(cli.sys, "argv", [str(entry)])

    assert ui.App(ui.Text("App")).asset_root == project


def test_cli_rejects_missing_application_file(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["run"]) == 2
    assert "application file not found" in capsys.readouterr().err


def test_cli_rejects_public_bind_and_invalid_port(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("# app\n", encoding="utf-8")
    assert cli.main(["run", "--host", "0.0.0.0"]) == 2
    assert "loopback" in capsys.readouterr().err
    assert cli.main(["run", "--port", "65536"]) == 2
    assert "between 0 and 65535" in capsys.readouterr().err


def test_cli_create_generates_importable_starter_and_protects_existing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["create", "my_app"]) == 0
    project = tmp_path / "my_app"
    assert {"app.py", "pyproject.toml", "README.md", "tests/test_app.py", "my_app/__init__.py", "assets/.gitkeep"} <= {
        str(path.relative_to(project)) for path in project.rglob("*") if path.is_file()
    }
    monkeypatch.syspath_prepend(str(project))
    from app import MainPage

    assert MainPage().to_dict(lambda callback: "event")["type"] == "column"
    with pytest.raises(FileExistsError):
        cli._create("my_app", tmp_path)


@pytest.mark.parametrize("name", ["../outside", "-app", "has space", "class"])
def test_cli_create_rejects_invalid_names(name, tmp_path):
    with pytest.raises(ValueError):
        cli._create(name, tmp_path)


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["--version"])
    assert error.value.code == 0
    assert "novaui" in capsys.readouterr().out


def test_cli_check_compiles_and_runs_tests_when_present(tmp_path, monkeypatch):
    (tmp_path / "ok.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    import pytest

    monkeypatch.setattr(pytest, "main", lambda args: pytest.ExitCode.OK)
    assert cli._check(tmp_path) == 0


def test_cli_check_returns_syntax_failure(tmp_path, capsys):
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    assert cli._check(tmp_path) == 1
    assert "syntax failed" in capsys.readouterr().err


def test_check_metadata_allows_arrays_before_project_version(tmp_path, capsys):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = []\nname = "sample"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    assert cli._check(tmp_path) == 0
    assert "Package metadata: passed" in capsys.readouterr().out


def test_config_rejects_unknown_fields(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[tool.novaui]\nunknown = "x"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown tool.novaui setting"):
        cli._read_project_config(tmp_path)


def test_cli_build_invokes_standard_build_frontend(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs)) or type(
            "Result", (), {"returncode": 0, "stdout": "built wheel and sdist\n", "stderr": ""}
        )(),
    )
    assert cli._build(tmp_path / "dist", tmp_path) == 0
    assert calls[0][0][1:3] == ["-m", "build"]


def test_cli_build_failure_is_actionable(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 1, "stdout": "", "stderr": "No module named build\n"}
        )(),
    )
    assert cli._build(tmp_path / "dist", tmp_path) == 1
    assert "novaui[build]" in capsys.readouterr().err
