from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mongod_config_documents_grpc_requirement():
    config = (ROOT / "config" / "mongod.conf").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    configuration_doc = (ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")

    assert "useGrpcForSearch: true" in config
    assert "supported by official MongoDB Community Server starting with 8.1" in config
    assert "MongoDB must be 8.1+" in env_example
    assert "MongoDB must be **8.1+**" in configuration_doc
    assert "do NOT set the Percona-specific flags" not in config
