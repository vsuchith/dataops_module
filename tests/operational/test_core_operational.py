"""Operational acceptance: core deployment profile compose parity."""

from pathlib import Path

import yaml


def test_core_compose_files_exist_and_parse() -> None:
    root = Path(__file__).resolve().parents[2]
    compose_dir = root / "deploy" / "docker" / "compose"
    core = compose_dir / "docker-compose.core.yml"
    assert core.exists()
    payload = yaml.safe_load(core.read_text(encoding="utf-8"))
    assert "services" in payload
    service_names = " ".join(payload["services"])
    assert "minio" in service_names
    assert "lakefs" in service_names

    for overlay in ("fraud", "cv", "litellm"):
        overlay_path = compose_dir / f"docker-compose.{overlay}.yml"
        assert overlay_path.exists(), f"missing overlay {overlay}"
        overlay_payload = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
        assert isinstance(overlay_payload, dict)
