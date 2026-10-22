"""Domain errors for the DataOps kernel."""


class DataOpsError(Exception):
    """Base error for kernel operations."""


class ValidationError(DataOpsError):
    """Contract or invariant violation."""


class ArtifactNotFoundError(DataOpsError):
    """Requested artifact version does not exist."""


class ChecksumMismatchError(DataOpsError):
    """Stored bytes do not match the declared checksum."""


class ImmutableVersionError(DataOpsError):
    """An existing artifact version cannot be overwritten with different content."""


class ImmutableMetadataError(DataOpsError):
    """Lifecycle or protected metadata cannot change outside promotion."""


class PromotionConsistencyError(DataOpsError):
    """Lakehouse promotion transaction failed or was rolled back."""
