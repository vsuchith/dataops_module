"""
Fail-closed capability registry for PIPELINE_MODE loading (ADR-006).

Selected modes must load required capability packs or raise CapabilityError.
Unselected optional integrations may remain absent without failing startup.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple


class CapabilityError(RuntimeError):
    """Selected pipeline mode cannot load a required capability pack."""

    def __init__(self, mode: str, pack: str, reason: str):
        self.mode = mode
        self.pack = pack
        self.reason = reason
        super().__init__(
            f"PIPELINE_MODE={mode!r} requires capability pack {pack!r} but it "
            f"failed to load: {reason}. Install optional dependencies "
            f"(e.g. pip install -e '.[cv]' for cvops) or choose a different "
            f"PIPELINE_MODE."
        )


@dataclass(frozen=True)
class CapabilityPack:
    """Declarative capability pack with required module exports."""

    name: str
    module_path: str
    required_items: Tuple[str, ...]
    min_non_empty: Tuple[str, ...] = ()

    def load(self, *, mode: str, required: bool) -> Dict[str, Any]:
        try:
            module = importlib.import_module(self.module_path)
        except ImportError as exc:
            if required:
                raise CapabilityError(mode, self.name, str(exc)) from exc
            return {}

        result: Dict[str, Any] = {}
        missing: List[str] = []
        for item in self.required_items:
            if not hasattr(module, item):
                missing.append(item)
            else:
                result[item] = getattr(module, item)

        if missing:
            if required:
                raise CapabilityError(
                    mode,
                    self.name,
                    f"missing exports: {', '.join(missing)}",
                )
            return {}

        for item in self.min_non_empty:
            value = result.get(item)
            if not value:
                if required:
                    raise CapabilityError(
                        mode,
                        self.name,
                        f"{item} is empty — capability pack incomplete",
                    )
                return {}

        return result


CAPABILITY_PACKS: Dict[str, CapabilityPack] = {
    "cvops": CapabilityPack(
        name="cvops",
        module_path="src.cvops.pipelines",
        required_items=(
            "CVOPS_ASSETS",
            "CVOPS_JOBS",
            "CVOPS_RESOURCES",
            "CVOPS_SENSORS",
            "CVOPS_CHECKS",
            "cvops_cleanup_job",
        ),
        min_non_empty=("CVOPS_ASSETS", "CVOPS_JOBS"),
    ),
    "llmops": CapabilityPack(
        name="llmops",
        module_path="src.llmops.pipelines",
        required_items=("LLMOPS_ASSETS", "LLMOPS_JOBS"),
        min_non_empty=("LLMOPS_ASSETS", "LLMOPS_JOBS"),
    ),
}

MODE_REQUIRED_PACKS: Dict[str, Tuple[str, ...]] = {
    "mlops": (),
    "cvops": ("cvops",),
    "llmops": ("llmops",),
    "combined": ("cvops", "llmops"),
}


def required_packs_for_mode(mode: str) -> Sequence[str]:
    return MODE_REQUIRED_PACKS.get(mode, MODE_REQUIRED_PACKS["combined"])


def load_capability_pack(pack_name: str, *, mode: str, required: bool) -> Dict[str, Any]:
    pack = CAPABILITY_PACKS.get(pack_name)
    if pack is None:
        return {}
    return pack.load(mode=mode, required=required)


def validate_mode_definitions(mode: str, assets: Sequence[Any], jobs: Sequence[Any]) -> None:
    """Fail closed when a selected mode produced an empty pipeline."""
    if not assets:
        raise CapabilityError(
            mode,
            mode,
            "no assets loaded — required capability pack missing or incomplete",
        )
    if mode in ("mlops", "combined") and not jobs:
        raise CapabilityError(
            mode,
            mode,
            "no jobs loaded — MLOps capability incomplete",
        )
