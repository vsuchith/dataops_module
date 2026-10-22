"""Compatibility layer between legacy packs and the DataOps kernel."""

from src.compatibility.fraud.api import validate_transaction
from src.compatibility.fraud.profile import FraudDetectionProfile, load_fraud_profile

__all__ = [
    "FraudDetectionProfile",
    "load_fraud_profile",
    "validate_transaction",
]
