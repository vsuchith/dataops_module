"""MLOps profile integration (E2.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from src.compatibility.fraud.profile import (
    load_fraud_profile,
    profile_is_explicitly_selected,
    profile_path_from_env,
)


def load_fraud_profile_config() -> Optional[dict[str, Any]]:
    path = profile_path_from_env()
    if path is None:
        return None
    profile = load_fraud_profile(path)
    return profile.model_dump()


def resolve_profile_path() -> Optional[Path]:
    return profile_path_from_env()


def load_profile_bronze_config() -> Optional[dict[str, Any]]:
    """Load bronze config from selected profile; fail closed on errors."""
    if not profile_is_explicitly_selected():
        return None
    from src.compatibility.fraud.mlops_bridge import bronze_sources_from_profile

    profile_path = profile_path_from_env()
    if profile_path is None:
        raise RuntimeError("fraud profile selected but path could not be resolved")
    if not profile_path.exists():
        raise FileNotFoundError(f"fraud profile not found: {profile_path}")
    return bronze_sources_from_profile(profile_path)
