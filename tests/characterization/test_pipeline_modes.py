"""Characterization tests lock legacy pipeline behavior before E2+ refactors."""

import importlib
import os
import sys

import pytest

# Project root on path (parent of tests/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _reload_pipelines():
    """Reload pipelines after PIPELINE_MODE changes."""
    import src.pipelines
    import src.pipelines.capability_registry as registry

    importlib.reload(registry)
    return importlib.reload(src.pipelines)


@pytest.fixture
def pipeline_mode(monkeypatch):
    """Set PIPELINE_MODE for get_definitions() without re-importing the module."""

    def _set(mode: str):
        monkeypatch.setenv("PIPELINE_MODE", mode)
        import src.pipelines as pipelines

        return pipelines

    return _set


class TestPublicImports:
    def test_pipelines_get_definitions_importable(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_MODE", "mlops")
        for key in list(sys.modules):
            if key.startswith("src.pipelines"):
                del sys.modules[key]
        from src.pipelines import get_definitions

        assert callable(get_definitions)

    def test_core_settings_importable(self):
        from src.core.config import settings

        assert settings is not None

    def test_fraud_api_models_importable(self):
        from src.core.api.models import PredictionResponse, TransactionRequest

        assert TransactionRequest is not None
        assert PredictionResponse is not None


class TestPipelineModeLoading:
    def test_mlops_mode_loads_assets(self, pipeline_mode):
        pipelines = pipeline_mode("mlops")
        if pipelines.get_definitions is None:
            pytest.skip("Dagster not installed")

        defs = pipelines.get_definitions()
        assert len(defs.assets) > 0
        assert len(defs.jobs) > 0

    def test_llmops_mode_loads_stub_assets(self, pipeline_mode):
        pipelines = pipeline_mode("llmops")
        if pipelines.get_definitions is None:
            pytest.skip("Dagster not installed")

        defs = pipelines.get_definitions()
        assert len(defs.assets) > 0
        assert len(defs.jobs) > 0

    def test_combined_mode_loads_all_packs_when_cv_deps_available(self, pipeline_mode):
        pipelines = pipeline_mode("combined")
        if pipelines.get_definitions is None:
            pytest.skip("Dagster not installed")

        defs = pipelines.get_definitions()
        assert len(defs.assets) > 0
        assert len(defs.jobs) > 0


class TestCapabilityRegistryFailClosed:
    def test_cvops_mode_raises_when_capability_missing(self, monkeypatch):
        from src.pipelines.capability_registry import CapabilityError, load_capability_pack

        original_import = importlib.import_module

        def failing_import(name, package=None):
            if name == "src.cvops.pipelines":
                raise ImportError("simulated missing cvops dependency")
            return original_import(name, package)

        monkeypatch.setattr(importlib, "import_module", failing_import)
        for key in list(sys.modules):
            if key.startswith("src.cvops"):
                del sys.modules[key]

        with pytest.raises(CapabilityError) as exc_info:
            load_capability_pack("cvops", mode="cvops", required=True)

        assert "cvops" in str(exc_info.value).lower()
        assert "PIPELINE_MODE='cvops'" in str(exc_info.value)

    def test_get_definitions_fail_closed_for_selected_cvops_mode(
        self, pipeline_mode, monkeypatch
    ):
        import src.pipelines.capability_registry as registry

        pipeline_mode("cvops")

        original_import = importlib.import_module

        def failing_import(name, package=None):
            if name == "src.cvops.pipelines":
                raise ImportError("simulated missing cvops dependency")
            return original_import(name, package)

        monkeypatch.setattr(importlib, "import_module", failing_import)
        for key in list(sys.modules):
            if key.startswith("src.cvops"):
                del sys.modules[key]

        with pytest.raises(registry.CapabilityError):
            registry.load_capability_pack("cvops", mode="cvops", required=True)

    def test_module_defs_raises_when_selected_mode_incomplete(
        self, monkeypatch,
    ):
        """Module-level defs must not swallow CapabilityError (ADR-006)."""
        monkeypatch.setenv("PIPELINE_MODE", "cvops")

        original_import = importlib.import_module

        def failing_import(name, package=None):
            if name == "src.cvops.pipelines":
                raise ImportError("simulated missing cvops dependency")
            return original_import(name, package)

        monkeypatch.setattr(importlib, "import_module", failing_import)
        for key in list(sys.modules):
            if key.startswith(("src.pipelines", "src.cvops")):
                del sys.modules[key]

        with pytest.raises(Exception) as exc_info:
            importlib.import_module("src.pipelines")

        assert type(exc_info.value).__name__ == "CapabilityError"
