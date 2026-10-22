"""
Unified Lakehouse Pipeline Definitions (Dagster)
=================================================

Set PIPELINE_MODE environment variable:
  - mlops: Only MLOps pipeline
  - cvops: Only CVOps pipeline
  - llmops: Only LLMOps pipeline
  - combined: All pipelines (default)

Direct imports from canonical paths:
    from src.core.config import settings, TRINO_CATALOG
    from src.core.resources import TrinoResource, LakeFSResource
    from src.mlops.pipelines.feature_transformer import FeatureContract
"""

import os
from typing import Any, Dict, List, Tuple

from src.pipelines.capability_registry import (
    CapabilityError,
    load_capability_pack,
    required_packs_for_mode,
    validate_mode_definitions,
)

# =============================================================================
# DAGSTER DEFINITIONS
# =============================================================================

# Initialize these so they exist even if Dagster isn't available
defs = None
get_definitions = None
SHARED_RESOURCES = {}

__all__ = ["defs", "get_definitions", "SHARED_RESOURCES", "CapabilityError"]

try:
    from dagster import Definitions
    from src.core.resources import (
        LakeFSResource, TrinoResource, MinIOResource,
        LabelStudioResource, AirbyteResource, NessieResource, FeastResource,
    )

    # =========================================================================
    # OPTIONAL IMPORT HELPER (unselected capability extensions only)
    # =========================================================================

    def optional_import(module_path: str, items: List[str], default: Any = None) -> Dict[str, Any]:
        """Import optional MLOps extensions; absent packs stay empty (ADR-006)."""
        result: Dict[str, Any] = {}
        try:
            module = __import__(module_path, fromlist=items)
            for item in items:
                result[item] = getattr(module, item, default)
        except ImportError:
            for item in items:
                result[item] = [] if isinstance(default, list) else default
        return result

    # =========================================================================
    # RESOURCES
    # =========================================================================

    SHARED_RESOURCES = {
        "lakefs": LakeFSResource(),
        "trino": TrinoResource(),
        "minio": MinIOResource(),
        "ls": LabelStudioResource(),
        "label_studio": LabelStudioResource(),
        "airbyte": AirbyteResource(),
        "nessie": NessieResource(),
        "feast": FeastResource(),
    }

    # =========================================================================
    # MLOPS CORE (required for mlops/combined modes)
    # =========================================================================

    from src.mlops.pipelines import (
        mlops_init_lakefs, mlops_airbyte_sync, mlops_promote_to_production,
        mlops_ingestion_job, mlops_promotion_job,
        mlops_init_iceberg_optimizations,
        mlops_bronze_ingestion,
        mlops_notify_jupyter, silver_table_sensor, mlops_labelstudio_export_job,
        mlops_ensure_review_columns, mlops_export_to_labelstudio,
        mlops_notify_labelstudio, mlops_merge_annotations,
        labelstudio_annotations_sensor, mlops_labelstudio_merge_job,
        mlops_gold_table,
        FEATURE_PIPELINE_ASSETS, FEATURE_PIPELINE_JOBS,
        MLOPS_ALL_CHECKS as MLOPS_CHECKS,
    )

    MLOPS_CORE_ASSETS = [
        mlops_init_lakefs, mlops_airbyte_sync, mlops_bronze_ingestion,
        mlops_notify_jupyter, mlops_ensure_review_columns, mlops_export_to_labelstudio,
        mlops_notify_labelstudio, mlops_merge_annotations, mlops_gold_table,
        mlops_init_iceberg_optimizations,
        mlops_promote_to_production,
    ]
    MLOPS_CORE_JOBS = [
        mlops_ingestion_job, mlops_labelstudio_export_job,
        mlops_labelstudio_merge_job, mlops_promotion_job,
    ]
    MLOPS_CORE_SENSORS = [silver_table_sensor, labelstudio_annotations_sensor]

    # =========================================================================
    # OPTIONAL MLOPS EXTENSIONS
    # =========================================================================

    q = optional_import("src.mlops.pipelines.quality_assets", [
        "bronze_quality_check", "silver_quality_check", "gold_quality_check", "training_quality_gate"
    ])
    QUALITY_ASSETS = [v for v in q.values() if v]

    m = optional_import("src.mlops.pipelines.drift_monitoring", [
        "drift_monitoring_report", "feature_drift_analysis", "data_quality_monitoring", "monitoring_summary"
    ])
    MONITORING_ASSETS = [v for v in m.values() if v]

    e = optional_import(
        "src.mlops.pipelines.mlops_evaluation",
        ["EVALUATION_ASSETS", "EVALUATION_JOBS", "EVALUATION_SCHEDULES"],
        [],
    )
    EVALUATION_ASSETS = e.get("EVALUATION_ASSETS", [])
    EVALUATION_JOBS = e.get("EVALUATION_JOBS", [])
    EVALUATION_SCHEDULES = e.get("EVALUATION_SCHEDULES", [])

    p = optional_import(
        "src.mlops.pipelines.performance_monitoring",
        ["PERFORMANCE_MONITORING_ASSETS", "performance_monitoring_job"],
    )
    PERFORMANCE_ASSETS = p.get("PERFORMANCE_MONITORING_ASSETS") or []
    PERFORMANCE_JOBS = [p.get("performance_monitoring_job")] if p.get("performance_monitoring_job") else []

    s = optional_import("src.mlops.pipelines.streaming_consumer", ["kafka_to_redis_sensor"])
    STREAMING_SENSORS = [s.get("kafka_to_redis_sensor")] if s.get("kafka_to_redis_sensor") else []

    r = optional_import("src.mlops.pipelines.auto_retrain_sensor", ["AUTO_RETRAIN_SENSORS"], [])
    AUTO_RETRAIN_SENSORS = r.get("AUTO_RETRAIN_SENSORS", [])

    i = optional_import("src.mlops.pipelines.iceberg_snapshot_sensor", ["ICEBERG_SNAPSHOT_SENSORS"], [])
    ICEBERG_SNAPSHOT_SENSORS = i.get("ICEBERG_SNAPSHOT_SENSORS", [])

    rs = optional_import("src.mlops.pipelines.rollback_sync", ["ROLLBACK_SYNC_JOBS"], [])
    ROLLBACK_SYNC_JOBS = rs.get("ROLLBACK_SYNC_JOBS", [])

    w = optional_import("src.mlops.pipelines.mlops_maintenance", ["lakefs_webhook_sensor", "lakefs_webhook_cleanup_job"])
    WEBHOOK_SENSORS = [w.get("lakefs_webhook_sensor")] if w.get("lakefs_webhook_sensor") else []
    WEBHOOK_JOBS = [w.get("lakefs_webhook_cleanup_job")] if w.get("lakefs_webhook_cleanup_job") else []

    # =========================================================================
    # MODE CONFIGURATION
    # =========================================================================

    MLOPS_ALL_ASSETS = (
        MLOPS_CORE_ASSETS + FEATURE_PIPELINE_ASSETS + QUALITY_ASSETS
        + MONITORING_ASSETS + EVALUATION_ASSETS + PERFORMANCE_ASSETS
    )
    MLOPS_ALL_JOBS = (
        MLOPS_CORE_JOBS + FEATURE_PIPELINE_JOBS + WEBHOOK_JOBS
        + EVALUATION_JOBS + PERFORMANCE_JOBS + ROLLBACK_SYNC_JOBS
    )
    MLOPS_ALL_SENSORS = (
        MLOPS_CORE_SENSORS + STREAMING_SENSORS + WEBHOOK_SENSORS
        + AUTO_RETRAIN_SENSORS + ICEBERG_SNAPSHOT_SENSORS
    )

    def _load_mode_capabilities(mode: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Load required capability packs for the selected mode (fail-closed)."""
        required = set(required_packs_for_mode(mode))
        cv: Dict[str, Any] = {}
        llm: Dict[str, Any] = {}

        if "cvops" in required:
            cv = load_capability_pack("cvops", mode=mode, required=True)
        else:
            cv = load_capability_pack("cvops", mode=mode, required=False)

        if "llmops" in required:
            llm = load_capability_pack("llmops", mode=mode, required=True)
        else:
            llm = load_capability_pack("llmops", mode=mode, required=False)

        return cv, llm

    def _build_mode_config(mode: str) -> Dict[str, Any]:
        cv, llm = _load_mode_capabilities(mode)

        cvops_assets = cv.get("CVOPS_ASSETS", [])
        cvops_jobs = list(cv.get("CVOPS_JOBS", []))
        if cv.get("cvops_cleanup_job"):
            cvops_jobs.append(cv["cvops_cleanup_job"])

        llmops_assets = llm.get("LLMOPS_ASSETS", [])
        llmops_jobs = llm.get("LLMOPS_JOBS", [])

        return {
            "mlops": {
                "assets": MLOPS_ALL_ASSETS,
                "jobs": MLOPS_ALL_JOBS,
                "sensors": MLOPS_ALL_SENSORS,
                "schedules": EVALUATION_SCHEDULES,
                "checks": MLOPS_CHECKS,
                "resources": {},
            },
            "cvops": {
                "assets": cvops_assets,
                "jobs": cvops_jobs,
                "sensors": cv.get("CVOPS_SENSORS", []),
                "schedules": [],
                "checks": cv.get("CVOPS_CHECKS", []),
                "resources": cv.get("CVOPS_RESOURCES") or {},
            },
            "llmops": {
                "assets": llmops_assets,
                "jobs": llmops_jobs,
                "sensors": [],
                "schedules": [],
                "checks": [],
                "resources": {},
            },
            "combined": {
                "assets": MLOPS_ALL_ASSETS + cvops_assets + llmops_assets,
                "jobs": MLOPS_ALL_JOBS + cvops_jobs + llmops_jobs,
                "sensors": MLOPS_ALL_SENSORS + cv.get("CVOPS_SENSORS", []),
                "schedules": EVALUATION_SCHEDULES,
                "checks": MLOPS_CHECKS + cv.get("CVOPS_CHECKS", []),
                "resources": cv.get("CVOPS_RESOURCES") or {},
            },
        }[mode]

    # =========================================================================
    # BUILD DEFINITIONS
    # =========================================================================

    def get_definitions() -> Definitions:
        """Create Dagster definitions based on PIPELINE_MODE."""
        mode = os.getenv("PIPELINE_MODE", "combined").lower()
        if mode not in ("mlops", "cvops", "llmops", "combined"):
            mode = "combined"

        config = _build_mode_config(mode)

        print(f"[Dagster] Mode: {mode.upper()}")

        resources = SHARED_RESOURCES.copy()
        resources.update(config.get("resources", {}))

        assets = [a for a in config.get("assets", []) if a]
        jobs = [j for j in config.get("jobs", []) if j]
        sensors = [s for s in config.get("sensors", []) if s]
        checks = [c for c in config.get("checks", []) if c]
        schedules = config.get("schedules", [])

        validate_mode_definitions(mode, assets, jobs)

        print(f"[Dagster] {len(assets)} assets, {len(jobs)} jobs, {len(sensors)} sensors")

        return Definitions(
            assets=assets,
            jobs=jobs,
            resources=resources,
            asset_checks=checks or None,
            schedules=schedules or None,
            sensors=sensors or None,
        )

    defs = get_definitions()

except ImportError:
    # Dagster not installed
    pass
