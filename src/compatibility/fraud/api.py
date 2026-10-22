"""Fraud API compatibility — validate requests via profile."""

from __future__ import annotations

from typing import Any

from src.compatibility.fraud.profile import load_fraud_profile, profile_path_from_env
from src.core.api.models import TransactionRequest


def validate_transaction(transaction: dict[str, Any]) -> dict[str, Any]:
    path = profile_path_from_env()
    if path is None:
        return transaction
    profile = load_fraud_profile(path)
    bronze = profile.dataset("bronze")
    if bronze.primary_key not in transaction:
        raise ValueError(f"missing required field: {bronze.primary_key}")
    return transaction


def validate_transaction_request(transaction: TransactionRequest) -> TransactionRequest:
    """Apply profile validation to a fraud API request model."""
    validate_transaction(transaction.model_dump())
    return transaction
