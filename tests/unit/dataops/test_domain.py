"""Domain model unit tests."""

import pytest

from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState, Checksum
from src.dataops.domain.errors import ValidationError


def _sample_ref(*, state: ArtifactState = ArtifactState.DRAFT) -> ArtifactRef:
    return ArtifactRef(
        artifact_id="art-1",
        version="v1",
        kind=ArtifactKind.GENERIC,
        uri="file:///tmp/art-1",
        checksum=Checksum(value="a" * 64),
        state=state,
    )


def test_artifact_identity_key() -> None:
    ref = _sample_ref()
    assert ref.identity_key() == "art-1@v1"


def test_legal_state_transition() -> None:
    ref = _sample_ref()
    ref.transition_to(ArtifactState.VALIDATED)
    ref.transition_to(ArtifactState.PUBLISHED)
    assert ref.state == ArtifactState.PUBLISHED


def test_illegal_state_transition() -> None:
    ref = _sample_ref(state=ArtifactState.PUBLISHED)
    with pytest.raises(ValidationError):
        ref.transition_to(ArtifactState.DRAFT)


def test_tombstoned_not_readable() -> None:
    ref = _sample_ref(state=ArtifactState.TOMBSTONED)
    with pytest.raises(ValidationError):
        ref.ensure_readable()
