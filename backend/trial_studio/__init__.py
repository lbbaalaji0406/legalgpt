"""
SAULGPT TRIAL STUDIO PACKAGE
============================
Pre-Trial Adversarial Intelligence Studio and 50,000+ Precedent Matrix.
"""

from .schema import (
    PrecedentDossier,
    TrialStudioStartRequest,
    TrialStudioTurnRequest,
    TrialStudioConcludeRequest,
    AdversarialTurnResponse
)
from .precedent_engine import PrecedentEngine, get_precedent_engine
from .cross_examiner_agent import HostileCrossExaminerAgent
from .defense_fortifier_agent import DefenseStrategistAgent

__all__ = [
    "PrecedentDossier",
    "TrialStudioStartRequest",
    "TrialStudioTurnRequest",
    "TrialStudioConcludeRequest",
    "AdversarialTurnResponse",
    "PrecedentEngine",
    "get_precedent_engine",
    "HostileCrossExaminerAgent",
    "DefenseStrategistAgent"
]
