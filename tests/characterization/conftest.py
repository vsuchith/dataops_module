"""Characterization tests require real Dagster (unit tests mock it in tests/conftest.py)."""

import importlib
import os
import sys
from unittest.mock import MagicMock


def _ensure_real_dagster() -> None:
    for name in ("dagster", "dagster_mlflow"):
        if isinstance(sys.modules.get(name), MagicMock):
            del sys.modules[name]
    importlib.import_module("dagster")


_ensure_real_dagster()
os.environ.setdefault("PIPELINE_MODE", "mlops")

for key in list(sys.modules):
    if key.startswith("src.pipelines"):
        del sys.modules[key]
