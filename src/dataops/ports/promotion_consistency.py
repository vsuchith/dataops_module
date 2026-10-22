"""Promotion consistency port (ADR-009)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.dataops.domain.promotion import PromotionReceipt, PromotionRequest


@runtime_checkable
class PromotionConsistencyPort(Protocol):
    def promote(self, request: PromotionRequest) -> PromotionReceipt: ...

    def rollback(self, receipt: PromotionReceipt) -> PromotionReceipt: ...
