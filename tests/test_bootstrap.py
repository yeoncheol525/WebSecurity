import importlib
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
create_env = importlib.import_module("create_env")
network_config = importlib.import_module("network_config")
lab_support = importlib.import_module("lab_support")
setup = importlib.import_module("setup")


@pytest.fixture
def env_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(create_env, "ROOT", tmp_path)
    monkeypatch.setattr(create_env, "auto_bind", lambda: "192.168.67.21")
    monkeypatch.setattr(create_env, "validate_bind", lambda value: value)
    return tmp_path


def test_initial_secrets_are_unique_and_rerun_keeps_them(env_directory):
    create_env.main()
    path = env_directory / ".env"
    first = path.read_bytes()
    values = create_env.parse_env(path)
    assert values["BIND_ADDRESS"] == "192.168.67.21"
    assert len({values[key] for key in ("POSTGRES_PASSWORD", "CATALOG_READER_PASSWORD", "ORDER_SERVICE_PASSWORD")}) == 3
    assert values["DEMO_USER1_PASSWORD_HASH"].startswith("pbkdf2:sha256:1000000$")
    create_env.main()
    assert path.read_bytes() == first


def test_legacy_environment_and_sqlite_data_are_preserved(env_directory):
    original = "BIND_ADDRESS=192.168.186.128\nWEB_PORT=5000\n"
    (env_directory / ".env").write_text(original)
    (env_directory / "instance").mkdir()
    database = env_directory / "instance/minishop.sqlite3"
    database.write_bytes(b"unchanged legacy fixture")
    create_env.main()
    assert (env_directory / ".env.sqlite-backup").read_text() == original
    values = create_env.parse_env(env_directory / ".env")
    assert values["BIND_ADDRESS"] == "192.168.67.21"
    assert values["HTTP_PORT"] == "18080"
    assert database.read_bytes() == b"unchanged legacy fixture"


def test_incomplete_current_env_is_never_silently_rotated(env_directory):
    original = "POSTGRES_PASSWORD=existing-test-value\n"
    path = env_directory / ".env"
    path.write_text(original)
    with pytest.raises(ValueError, match="incomplete"):
        create_env.main()
    assert path.read_text() == original


def test_explicit_bind_change_keeps_passwords(env_directory):
    create_env.main()
    path = env_directory / ".env"
    before = create_env.parse_env(path)
    create_env.main("192.168.67.22")
    after = create_env.parse_env(path)
    assert after["BIND_ADDRESS"] == "192.168.67.22"
    assert all(after[key] == value for key, value in before.items() if key != "BIND_ADDRESS")


def test_auto_bind_excludes_nat_docker_and_inactive_devices():
    def interface(name, address, state="UP"):
        return {"ifname": name, "operstate": state,
                "addr_info": [{"family": "inet", "scope": "global", "local": address}]}
    addresses = [interface("uplink0", "192.168.186.130"), interface("docker0", "172.17.0.1"),
                 interface("br-example", "172.18.0.1"), interface("lab0", "192.168.67.21"),
                 interface("unused0", "192.168.70.10", "DOWN")]
    assert network_config.private_candidates(addresses, [{"dev": "uplink0"}]) == ["192.168.67.21"]


@pytest.mark.parametrize("condition", lab_support.EXPERIMENTS)
def test_experiment_selection_preserves_credentials_and_selects_compose(env_directory, monkeypatch, condition):
    create_env.main()
    before = create_env.parse_env(env_directory / ".env")
    monkeypatch.setattr(lab_support, "ROOT", env_directory)
    lab_support.select_experiment(condition)
    after = lab_support.read_env()
    assert lab_support.selected_experiment(after) == condition
    assert {k: v for k, v in after.items() if k != "LAB_EXPERIMENT"} == {
        k: v for k, v in before.items() if k != "LAB_EXPERIMENT"}

    commands = []
    monkeypatch.setattr(lab_support, "docker_prefix", lambda: ["docker"])
    monkeypatch.setattr(lab_support.subprocess, "run", lambda command, **kwargs: commands.append(command))
    monkeypatch.setenv("COMPOSE_FILE", "unrelated.yml")
    lab_support.compose("config", "--quiet")
    assert str(env_directory / "experiments" / condition / "compose.yml") in commands[0]
    assert "unrelated.yml" not in commands[0]


def test_invalid_saved_experiment_is_rejected():
    with pytest.raises(ValueError, match="LAB_EXPERIMENT"):
        lab_support.selected_experiment({"LAB_EXPERIMENT": "E5"})
    assert lab_support.selected_experiment({}) == "E4"  # Existing PostgreSQL .env files.


@pytest.mark.parametrize("condition", lab_support.EXPERIMENTS)
def test_setup_stops_at_service_startup_without_tests_or_reports(env_directory, monkeypatch, condition):
    monkeypatch.setattr(lab_support, "ROOT", env_directory)
    monkeypatch.setattr(setup, "read_env", lab_support.read_env)
    monkeypatch.setattr(setup, "validate_bind", lambda address: address)
    monkeypatch.setattr(setup, "docker_prefix", lambda: ["docker"])
    compose_calls, admin_calls, process_calls = [], [], []
    monkeypatch.setattr(setup, "compose", lambda *args, **kwargs: compose_calls.append(args))
    monkeypatch.setattr(setup, "admin_sql", lambda statement: admin_calls.append(statement))
    monkeypatch.setattr(setup.subprocess, "run", lambda command, **kwargs: process_calls.append(command))
    monkeypatch.setattr(sys, "argv", ["setup.py", "--experiment", condition])
    setup.main()
    assert lab_support.selected_experiment() == condition
    assert all("tester" not in call and "verification" not in call for call in compose_calls)
    assert all("verify_environment.py" not in " ".join(call) for call in process_calls)
    assert not (env_directory / "results").exists()
    if condition in ("E1", "E2"):
        assert "LOGIN VALID UNTIL 'infinity'" in admin_calls[0]
    else:
        assert "NOLOGIN" in admin_calls[0]


def test_setup_cannot_opt_into_verification(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["setup.py", "--verify"])
    with pytest.raises(SystemExit) as caught:
        setup.main()
    assert caught.value.code == 2
