"""
SAULGPT TRIAL STUDIO — DATA SCHEMAS
====================================
Standardized data contracts for the 50,000+ Precedent Judgment Engine,
Ratio Decidendi Extraction, and Dual Adversarial Agents.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PrecedentDossier(BaseModel):
    """
    Structured representation of a controlling Indian trial or appellate judgment.
    """
    case_id: str = Field(..., description="Unique case identifier, e.g. 'SC-2019-CRIM-138-042'")
    citation: str = Field(..., description="Official Law Report citation (e.g., '(2019) 4 SCC 197')")
    title: str = Field(..., description="Parties to the dispute, e.g. 'Bir Singh v. Mukesh Kumar'")
    court: str = Field(..., description="Adjudicating bench: Supreme Court, High Court of Delhi, NCDRC, etc.")
    year: int = Field(..., description="Year of judgment")
    act: str = Field(..., description="Primary governing Act out of the 8 Core Acts")
    sections_invoked: List[str] = Field(default_factory=list, description="Sections applied (e.g. ['Sec 138', 'Sec 139'])")
    
    fact_anchor: str = Field(..., description="Core factual pattern that triggered the dispute")
    evidence_tendered: List[str] = Field(default_factory=list, description="Documents & oral testimony produced in trial")
    evidence_admissibility: Dict[str, Any] = Field(
        default_factory=dict,
        description="Rulings on admissibility (e.g., Sec 63 BSA / 65B IEA certificate status, electronic hash validity)"
    )
    cross_exam_turning_point: Dict[str, str] = Field(
        default_factory=dict,
        description="The decisive line of questioning that exposed the fatal contradiction or secured acquittal/conviction"
    )
    ratio_decidendi: str = Field(..., description="The binding legal proposition that decided the case")
    obiter_dicta: Optional[str] = Field(default="", description="Incidental judicial remarks (filtered out during ratio extraction)")
    statutory_presumptions: List[str] = Field(
        default_factory=list,
        description="Presumptions applied (e.g. 'Sec 139 NI Act reverse burden', 'Sec 114 BSA standard course of business')"
    )
    outcome: str = Field(..., description="Final judicial outcome: 'Acquitted', 'Convicted', 'Decreed', 'Dismissed'")
    vulnerability_tag: str = Field(..., description="Category of trial weakness: 'limitation_bar', 'cash_loan_itr_gap', 'sec_63_bsa_failure', 'privity_defect'")


class TrialStudioStartRequest(BaseModel):
    session_id: str
    scenario: str
    act_hint: Optional[str] = None
    mode: str = Field(default="moot_court", description="'moot_court' | 'cross_examiner' | 'defense_fortifier'")
    witness_role: str = Field(default="accused", description="'accused' (borrower/drawer/defendant) | 'complainant' (lender/payee/plaintiff)")
    evidence_id: Optional[str] = None
    grounded_evidence: Optional[Dict[str, Any]] = None


class TrialStudioTurnRequest(BaseModel):
    session_id: str
    witness_answer: str
    turn_index: int = 1
    witness_role: Optional[str] = Field(default=None, description="'accused' | 'complainant'")
    grounded_evidence: Optional[Dict[str, Any]] = None


class TrialStudioConcludeRequest(BaseModel):
    session_id: str


class AdversarialTurnResponse(BaseModel):
    mode: str
    turn_index: int
    interrogation_content: str = Field(..., description="Razor-sharp leading question (<= 2 questions, <= 60 words) or structured defense brief")
    vulnerability_score: int = Field(..., description="Current trial exposure score (0 - 100%)")
    vulnerability_delta: int = Field(default=0, description="Change in score after latest witness response")
    fatal_flaw_detected: Optional[str] = None
    precedent_backing: Optional[Dict[str, Any]] = None
    suggested_statutory_motions: List[str] = Field(default_factory=list)
    coach_advice: Optional[Dict[str, Any]] = Field(default=None, description="Structured Corner Coach tactical audit, objection, and rejoinder")
