import importlib
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
create_env = importlib.import_module("create_env")
network_config = importlib.import_module("network_config")


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
