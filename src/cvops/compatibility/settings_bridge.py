"""Map inline CVOps profile defaults to legacy CVOpsSettings."""

from src.core.config import CVOpsSettings
from src.cvops.compatibility.specs import (
    CvopsProfile,
    ImageSourceSpec,
    ManifestDatasetSpec,
    PromotionPolicySpec,
    QualityCheckSpec,
    StorageKind,
)


def manifest_table_fqn(settings: CVOpsSettings | None = None) -> str:
    cfg = settings or CVOpsSettings()
    return f"{cfg.manifest_schema}.{cfg.manifest_table}"


def default_cvops_profile() -> CvopsProfile:
    settings = CVOpsSettings()
    return CvopsProfile(
        profile_id="object_detection",
        version="1.0.0",
        lakefs_repo=settings.repo,
        lakefs_branch=settings.branch,
        raw_prefix=settings.raw_prefix,
        sources=[
            ImageSourceSpec(
                name="raw_images",
                storage_kind=StorageKind.LAKEFS if settings.use_lakefs_storage else StorageKind.S3,
                uri_prefix=f"lakefs://{settings.repo}/{settings.branch}/{settings.raw_prefix}",
                description="Default raw image source",
            )
        ],
        datasets=[
            ManifestDatasetSpec(
                name="manifest",
                dataset_id="cv.image_collection",
                artifact_id="cv.image_manifest",
                catalog_table=manifest_table_fqn(settings),
                source_ref="raw_images",
                schema_ref="manifest://cv/image_collection/v1",
            )
        ],
        quality_checks=[
            QualityCheckSpec(
                name="manifest_non_empty",
                severity="critical",
                rule="count(images) > 0",
            ),
            QualityCheckSpec(
                name="supported_formats_only",
                severity="warning",
                rule="format IN ('jpg','jpeg','png','webp')",
            ),
        ],
        promotion_policy=PromotionPolicySpec(
            min_training_samples=settings.min_training_samples,
        ),
    )


def cvops_settings_snapshot(profile: CvopsProfile) -> dict[str, str]:
    manifest = profile.dataset("manifest")
    source = profile.source(manifest.source_ref) if manifest.source_ref else profile.sources[0]
    if "." in manifest.catalog_table:
        schema_name, table_name = manifest.catalog_table.split(".", 1)
    else:
        schema_name, table_name = "", manifest.catalog_table
    return {
        "repo": profile.lakefs_repo,
        "branch": profile.lakefs_branch,
        "raw_prefix": profile.raw_prefix,
        "manifest_schema": schema_name,
        "manifest_table": table_name,
        "manifest_table_fqn": manifest.catalog_table,
        "uri_prefix": source.uri_prefix,
        "min_training_samples": str(profile.promotion_policy.min_training_samples),
    }
