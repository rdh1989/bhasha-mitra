from pathlib import Path

from infrastructure.configuration.configuration_manager import ConfigurationManager


def test_configuration_manager_resolves_relative_config_from_project_root(monkeypatch, tmp_path):
    ConfigurationManager._instance = None
    monkeypatch.chdir(tmp_path)

    configuration = ConfigurationManager()
    configuration.initialize()

    expected = Path(__file__).resolve().parents[1] / "config"
    assert configuration._config_directory == expected.resolve()
    assert (configuration._config_directory / "manifest.json").is_file()
