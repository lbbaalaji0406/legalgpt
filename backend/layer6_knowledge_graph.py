"""
SAULSGPT — LAYER 6: LEGAL KNOWLEDGE GRAPH
==========================================
Uses NetworkX to map institutional relationships across Indian law.
Acts as a high-speed (<1ms) post-retrieval context expander and reasoning anchor.

What it maps:
→ Act level replacements (IPC → BNS, CrPC → BNSS, IEA → BSA 2023)
→ Constitutional Overrides & Fundamental Rights (Articles 14, 19, 21, 22, 32, 226, 300A)
→ Criminal offences, punishments, and definitions (BNS / IPC)
→ Criminal procedure pipelines (Zero FIR → SP Escalation → S.156(3) Magistrate → S.482 Quashing)
→ Civil Procedure & Injunctions (Order 39, Order 7 Rule 11, Order 37 CPC)
→ Family & Matrimonial Law (HMA 13/24/25, HSA 6/8/30 Coparcenary, PWDVA 2005)
→ Commercial, Cheque Bounce & Arbitration (NI Act 138, S.27 Contract Act, Arb Act 1996)
→ Struck Down & Landmark Supreme Court Precedents (Shreya Singhal, Joseph Shine, Navtej Johar, Puttaswamy)
"""

import networkx as nx
from typing import List, Dict

# Canonical Act Aliases
ACT_ALIASES = {
    "ipc": "IPC", "indian penal code": "IPC", "indian penal code, 1860": "IPC", "ipc_from_db": "IPC",
    "crpc": "CrPC", "code of criminal procedure": "CrPC", "code of criminal procedure, 1973": "CrPC", "crpc_from_db": "CrPC",
    "iea": "IEA", "indian evidence act": "IEA", "indian evidence act, 1872": "IEA", "iea_from_db": "IEA",
    "bns": "BNS", "bns 2023": "BNS", "bharatiya nyaya sanhita": "BNS", "bharatiya nyaya sanhita 2023": "BNS",
    "bnss": "BNSS", "bnss 2023": "BNSS", "bharatiya nagarik suraksha sanhita": "BNSS", "bnss_from_db": "BNSS",
    "bsa": "BSA", "bsa 2023": "BSA", "bharatiya sakshya adhiniyam": "BSA", "bsa_from_db": "BSA",
    "cpc": "CPC", "code of civil procedure": "CPC", "code of civil procedure, 1908": "CPC", "cpc_from_db": "CPC",
    "constitution": "Constitution", "constitution of india": "Constitution", "the constitution of india": "Constitution",
    "hma": "HMA", "hindu marriage act": "HMA", "hindu marriage act, 1955": "HMA", "hma_from_db": "HMA",
    "hsa": "HSA", "hindu succession act": "HSA", "hindu succession act, 1956": "HSA",
    "nia": "NIA", "negotiable instruments act": "NIA", "negotiable instruments act, 1881": "NIA", "nia_from_db": "NIA",
    "ida": "IDA", "industrial disputes act": "IDA", "ida_from_db": "IDA",
    "mva": "MVA", "motor vehicles act": "MVA", "motor vehicles act, 1988": "MVA", "mva_from_db": "MVA",
    "pwdva": "PWDVA", "domestic violence act": "PWDVA", "protection of women from domestic violence act": "PWDVA"
}

def normalize_act_name(raw_name: str) -> str:
    return ACT_ALIASES.get(raw_name.lower().strip(), raw_name)


class LegalKnowledgeGraph:
    """
    Directed Knowledge Graph of Indian Law Relationships.
    Built once at startup; queried in sub-millisecond time.
    """

    def __init__(self):
        print("[Graph] Initializing Institutional Legal Knowledge Graph...")
        self.G = nx.DiGraph()
        self._build_graph()
        print(f"[Graph] Institutional Graph built: "
              f"{self.G.number_of_nodes()} nodes, "
              f"{self.G.number_of_edges()} edges\n")

    def _build_graph(self):
        """Builds the comprehensive Indian legal relationship graph."""

        # ── 1. MASTER ACT REPLACEMENTS (July 1, 2024) ──
        self.G.add_edge("IPC",  "BNS",  relation="replaced_by", date="2024-07-01")
        self.G.add_edge("CrPC", "BNSS", relation="replaced_by", date="2024-07-01")
        self.G.add_edge("IEA",  "BSA",  relation="replaced_by", date="2024-07-01")
        self.G.add_edge("Consumer_Protection_Act_1986", "Consumer_Protection_Act_2019", relation="replaced_by")
        self.G.add_edge("Companies_Act_1956", "Companies_Act_2013", relation="replaced_by")
        self.G.add_edge("Arbitration_Act_1940", "Arbitration_and_Conciliation_Act_1996", relation="replaced_by")
        self.G.add_edge("FERA_1973", "FEMA_1999", relation="replaced_by")
        self.G.add_edge("MRTP_Act_1969", "Competition_Act_2002", relation="replaced_by")

        # ── 2. CONSTITUTIONAL HIERARCHY & WRIT REMEDIES ──
        self.G.add_edge("Constitution", "IPC",  relation="overrides")
        self.G.add_edge("Constitution", "CrPC", relation="overrides")
        self.G.add_edge("Constitution", "BNS",  relation="overrides")
        self.G.add_edge("Constitution", "BNSS", relation="overrides")
        self.G.add_edge("Constitution", "CPC",  relation="overrides")

        self.G.add_edge("Article_14",   "Equal_Protection", relation="guarantees")
        self.G.add_edge("Article_19_1_a", "Free_Speech", relation="guarantees")
        self.G.add_edge("Free_Speech",  "Article_19_2", relation="subject_to_reasonable_restrictions")
        self.G.add_edge("Article_20_1", "No_Ex_Post_Facto_Law", relation="guarantees")
        self.G.add_edge("Article_20_2", "No_Double_Jeopardy", relation="guarantees")
        self.G.add_edge("Article_20_3", "Right_Against_Self_Incrimination", relation="guarantees")
        self.G.add_edge("Article_21",   "Right_to_Life_and_Liberty", relation="guarantees")
        self.G.add_edge("Article_21",   "Right_to_Fair_Trial", relation="encompasses")
        self.G.add_edge("Article_21",   "Right_to_Privacy", relation="encompasses")
        self.G.add_edge("Article_22",   "Arrest_Safeguards", relation="guarantees")
        self.G.add_edge("Article_32",   "Supreme_Court_Writs", relation="empowers")
        self.G.add_edge("Article_226",  "High_Court_Writs", relation="empowers")
        self.G.add_edge("Article_300A", "Right_to_Property", relation="protects_from_arbitrary_deprivation")

        # ── 3. CRIMINAL LAW (BNS 2023 / IPC 1860) ──
        # Murder & Homicide
        self.G.add_edge("IPC_302", "BNS_103", relation="replaced_by")
        self.G.add_edge("IPC_302", "IPC_300", relation="requires_definition_from")
        self.G.add_edge("IPC_302", "IPC_299", relation="distinguished_from")
        self.G.add_edge("IPC_302", "IPC_304", relation="lesser_offence")
        self.G.add_edge("BNS_103", "BNS_101", relation="requires_definition_from")

        # Theft, Extortion, Robbery
        self.G.add_edge("IPC_378", "BNS_303", relation="replaced_by")
        self.G.add_edge("IPC_379", "BNS_303_2", relation="replaced_by")
        self.G.add_edge("IPC_383", "BNS_308", relation="replaced_by")
        self.G.add_edge("IPC_384", "BNS_308_2", relation="replaced_by")
        self.G.add_edge("IPC_390", "BNS_309", relation="replaced_by")
        self.G.add_edge("IPC_392", "BNS_309_4", relation="replaced_by")

        # Cheating, Forgery, Fraud
        self.G.add_edge("IPC_415", "IPC_420", relation="defines")
        self.G.add_edge("IPC_420", "BNS_318", relation="replaced_by")
        self.G.add_edge("IPC_405", "IPC_406", relation="defines_criminal_breach_of_trust")
        self.G.add_edge("IPC_406", "BNS_316", relation="replaced_by")
        self.G.add_edge("IPC_463", "IPC_465", relation="defines_forgery")
        self.G.add_edge("IPC_465", "BNS_336", relation="replaced_by")
        self.G.add_edge("IPC_468", "BNS_338", relation="replaced_by")
        self.G.add_edge("IPC_471", "BNS_340", relation="replaced_by")

        # Hurt, Assault, Criminal Trespass
        self.G.add_edge("IPC_319", "IPC_323", relation="defines_simple_hurt")
        self.G.add_edge("IPC_323", "BNS_115", relation="replaced_by")
        self.G.add_edge("IPC_324", "BNS_118", relation="replaced_by")
        self.G.add_edge("IPC_320", "IPC_325", relation="defines_grievous_hurt")
        self.G.add_edge("IPC_325", "BNS_117", relation="replaced_by")
        self.G.add_edge("IPC_441", "IPC_447", relation="defines_criminal_trespass")
        self.G.add_edge("IPC_447", "BNS_329", relation="replaced_by")
        self.G.add_edge("IPC_425", "IPC_427", relation="defines_mischief_and_crop_damage")
        self.G.add_edge("IPC_427", "BNS_324", relation="replaced_by")
        self.G.add_edge("IPC_503", "IPC_506", relation="defines_criminal_intimidation")
        self.G.add_edge("IPC_506", "BNS_351", relation="replaced_by")

        # Matrimonial & Women Offences
        self.G.add_edge("IPC_498A", "BNS_85",  relation="replaced_by")
        self.G.add_edge("IPC_498A", "BNS_86",  relation="replaced_by")
        self.G.add_edge("IPC_498A", "Arnesh_Kumar_2014", relation="governed_by_arrest_guidelines")
        self.G.add_edge("IPC_304B", "BNS_80",  relation="replaced_by")
        self.G.add_edge("IPC_354",  "BNS_74",  relation="replaced_by")
        self.G.add_edge("IPC_354D", "BNS_78",  relation="replaced_by")
        self.G.add_edge("IPC_375",  "BNS_63",  relation="replaced_by")
        self.G.add_edge("IPC_376",  "BNS_64",  relation="replaced_by")

        # Defamation & Conspiracy
        self.G.add_edge("IPC_499",  "IPC_500", relation="defines_defamation")
        self.G.add_edge("IPC_500",  "BNS_356", relation="replaced_by")
        self.G.add_edge("IPC_120A", "IPC_120B", relation="defines_conspiracy")
        self.G.add_edge("IPC_120B", "BNS_61",  relation="replaced_by")

        # ── 4. CRIMINAL PROCEDURE (BNSS 2023 / CrPC 1973) ──
        # FIR & Police Escalation Ladder
        self.G.add_edge("FIR",              "CrPC_154",           relation="filed_under")
        self.G.add_edge("CrPC_154",         "BNSS_173",           relation="replaced_by")
        self.G.add_edge("Zero_FIR",         "BNSS_173_1",         relation="mandated_under")
        self.G.add_edge("Police_Refusal_FIR","CrPC_154_3",        relation="escalate_to_SP")
        self.G.add_edge("CrPC_154_3",       "BNSS_173_4",         relation="replaced_by")
        self.G.add_edge("SP_Refusal",       "CrPC_156_3",         relation="apply_to_Magistrate")
        self.G.add_edge("CrPC_156_3",       "BNSS_175_3",         relation="replaced_by")
        self.G.add_edge("CrPC_156_3",       "FIR_Registration_Order", relation="empowers_magistrate")

        # Investigation, Chargesheet & Trial
        self.G.add_edge("FIR",              "Police_Investigation", relation="triggers")
        self.G.add_edge("Police_Investigation", "Chargesheet",    relation="leads_to")
        self.G.add_edge("Chargesheet",      "CrPC_173",           relation="filed_under")
        self.G.add_edge("CrPC_173",         "BNSS_193",           relation="replaced_by")
        self.G.add_edge("Chargesheet",      "Magistrate_Cognizance", relation="leads_to")
        self.G.add_edge("Magistrate_Cognizance", "Trial",         relation="leads_to")
        self.G.add_edge("Trial",            "Judgment",           relation="leads_to")
        self.G.add_edge("Judgment",         "Appeal",             relation="appealable_in")

        # Land & Possession Peace Disputes (Executive Magistrate)
        self.G.add_edge("Land_Breach_of_Peace", "CrPC_145",       relation="governed_by")
        self.G.add_edge("CrPC_145",         "BNSS_164",           relation="replaced_by")
        self.G.add_edge("CrPC_145",         "Possession_Restoration", relation="empowers_SDM")
        self.G.add_edge("CrPC_145_3",       "Crop_Protection_Order", relation="preserves_perishable_crops")
        self.G.add_edge("Right_of_Way_Dispute", "CrPC_147",       relation="governed_by")
        self.G.add_edge("CrPC_147",         "BNSS_166",           relation="replaced_by")

        # Inherent Quashing Powers
        self.G.add_edge("Illegal_FIR",      "CrPC_482",           relation="quashing_petition")
        self.G.add_edge("CrPC_482",         "BNSS_528",           relation="replaced_by")
        self.G.add_edge("BNSS_528",         "High_Court",         relation="filed_before")

        # Arrest, Remand & Bail
        self.G.add_edge("CrPC_41",          "BNSS_35",            relation="replaced_by")
        self.G.add_edge("CrPC_41A",         "BNSS_35_3",          relation="notice_of_appearance")
        self.G.add_edge("CrPC_57",          "BNSS_58",            relation="24_hour_magistrate_production")
        self.G.add_edge("CrPC_167",         "BNSS_187",           relation="remand_and_default_bail")
        self.G.add_edge("CrPC_436",         "BNSS_478",           relation="bailable_offence_bail")
        self.G.add_edge("CrPC_437",         "BNSS_479",           relation="non_bailable_offence_bail")
        self.G.add_edge("CrPC_438",         "BNSS_482",           relation="anticipatory_bail")
        self.G.add_edge("CrPC_439",         "BNSS_483",           relation="special_bail_powers_sessions_hc")

        # Maintenance under Criminal Code
        self.G.add_edge("Wife_Maintenance", "CrPC_125",           relation="filed_under")
        self.G.add_edge("CrPC_125",         "BNSS_144",           relation="replaced_by")
        self.G.add_edge("BNSS_144",         "Interim_Maintenance_Order", relation="empowers_court")

        # ── 5. CIVIL PROCEDURE CODE (CPC 1908) & SPECIFIC RELIEF ──
        self.G.add_edge("CPC_Suit",         "CPC_Summons",        relation="triggers")
        self.G.add_edge("CPC_Summons",      "CPC_Written_Statement", relation="leads_to_30_to_90_days")
        self.G.add_edge("CPC_Written_Statement", "CPC_Trial",     relation="leads_to")
        self.G.add_edge("CPC_Trial",        "CPC_Decree",         relation="leads_to")
        self.G.add_edge("CPC_Decree",       "CPC_Appeal_S96",     relation="first_appeal")
        self.G.add_edge("CPC_Appeal_S96",   "CPC_Second_Appeal_S100", relation="second_appeal_on_substantial_law")

        self.G.add_edge("Defective_Plaint", "Order_7_Rule_11_CPC", relation="mandatory_rejection")
        self.G.add_edge("Order_7_Rule_11_CPC", "Limitation_Act_1963", relation="checks_limitation")
        self.G.add_edge("Order_7_Rule_11_CPC", "Court_Fees_Act_1870", relation="checks_valuation")
        self.G.add_edge("Stay_Order_Request","Order_39_Rule_1_2_CPC", relation="temporary_injunction")
        self.G.add_edge("Order_39_Rule_1_2_CPC", "Prima_Facie_Case", relation="requires")
        self.G.add_edge("Order_39_Rule_1_2_CPC", "Balance_of_Convenience", relation="requires")
        self.G.add_edge("Order_39_Rule_1_2_CPC", "Irreparable_Injury", relation="requires")
        self.G.add_edge("Debt_Recovery_Suit","Order_37_CPC",      relation="summary_suit")
        self.G.add_edge("ADR_Settlement",   "Section_89_CPC",     relation="mediation_arbitration_lok_adalat")

        # ── 6. FAMILY, MARRIAGE & SUCCESSION LAW ──
        # Hindu Marriage Act, 1955
        self.G.add_edge("HMA_13_1_i",       "Adultery_Ground",    relation="civil_ground_for_divorce")
        self.G.add_edge("HMA_13_1_ia",      "Cruelty_Ground",     relation="ground_for_divorce")
        self.G.add_edge("HMA_13_1_ib",      "Desertion_Ground",   relation="2_year_desertion_ground")
        self.G.add_edge("HMA_13B",          "Mutual_Consent_Divorce", relation="provides_for")
        self.G.add_edge("Mutual_Consent_Divorce", "Amardeep_Singh_2017", relation="6_month_cooling_off_waiver")
        self.G.add_edge("HMA_24",           "Interim_Maintenance_Pendente_Lite", relation="provides_for")
        self.G.add_edge("HMA_25",           "Permanent_Alimony",  relation="provides_for")
        self.G.add_edge("HMA_9",            "Restitution_of_Conjugal_Rights", relation="provides_for")

        # Hindu Succession Act, 1956
        self.G.add_edge("HSA_6",            "Daughters_Coparcenary_By_Birth", relation="guarantees")
        self.G.add_edge("Daughters_Coparcenary_By_Birth", "Vineeta_Sharma_2020", relation="supreme_court_benchmark")
        self.G.add_edge("HSA_8",            "Class_I_Legal_Heirs_Succession", relation="governs_self_acquired")
        self.G.add_edge("HSA_30",           "Testamentary_Will_of_Undivided_Share", relation="empowers_coparcener")
        self.G.add_edge("Ancestral_Property_Dispute", "Partition_Suit", relation="remedy_before_civil_court")

        # Domestic Violence Act (PWDVA 2005)
        self.G.add_edge("Domestic_Violence", "PWDVA_2005_S12",    relation="application_to_Magistrate")
        self.G.add_edge("PWDVA_2005_S12",   "PWDVA_S18",          relation="protection_orders")
        self.G.add_edge("PWDVA_2005_S12",   "PWDVA_S19",          relation="residence_orders")
        self.G.add_edge("PWDVA_2005_S12",   "PWDVA_S20",          relation="monetary_relief")
        self.G.add_edge("PWDVA_2005_S12",   "PWDVA_S21",          relation="temporary_custody")

        # ── 7. COMMERCIAL, BANKING, LABOUR & PROPERTY ──
        # Cheque Bounce (NI Act 1881)
        self.G.add_edge("Cheque_Dishonour", "NI_Act_138",         relation="criminal_offence")
        self.G.add_edge("NI_Act_138",       "NI_Act_138_b",       relation="requires_15_day_legal_notice")
        self.G.add_edge("NI_Act_138_b",     "NI_Act_142",         relation="30_day_magistrate_complaint_limitation")

        # Indian Contract Act, 1872
        self.G.add_edge("Non_Compete_Clause","Contract_Act_S27",  relation="void_in_restraint_of_trade")
        self.G.add_edge("Contract_Act_S27", "Percept_DMark_2006", relation="supreme_court_voidance_ruling")
        self.G.add_edge("Contract_Breach",  "Contract_Act_S73",   relation="actual_loss_damages")
        self.G.add_edge("Penalty_Clause",   "Contract_Act_S74",   relation="liquidated_damages_cap")

        # Arbitration & Conciliation Act, 1996
        self.G.add_edge("Arbitration_Interim_Relief", "Arbitration_Act_S9", relation="filed_before_court")
        self.G.add_edge("Arbitrator_Appointment", "Arbitration_Act_S11", relation="high_court_petition")
        self.G.add_edge("Unilateral_Arbitrator", "Arbitration_Act_S12_5", relation="void_ab_initio_TRF_Perkins")
        self.G.add_edge("Arbitral_Award_Challenge", "Arbitration_Act_S34", relation="setting_aside_petition")

        # Real Estate & Tenancy (RERA & TPA)
        self.G.add_edge("Delayed_Flat_Possession", "RERA_2016_S18", relation="refund_with_interest")
        self.G.add_edge("Tenant_Eviction",  "TPA_1882_S106",      relation="15_day_notice_to_quit")
        self.G.add_edge("Unregistered_Lease_Over_11_Months", "Registration_Act_S17", relation="inadmissible_as_lease")

        # Labour & Employment
        self.G.add_edge("Unpaid_Salary_Claim", "Payment_of_Wages_Act_S15", relation="claim_before_authority")
        self.G.add_edge("Minimum_Wages_Violation", "Minimum_Wages_Act_S22", relation="claim_before_Labour_Court")
        self.G.add_edge("Gratuity_Eligibility", "Payment_of_Gratuity_Act_S4", relation="5_years_continuous_service")

        # ── 8. STRUCK DOWN / UNCONSTITUTIONAL LANDMARK PRECEDENTS ──
        self.G.add_edge("ITA_66A",          "Shreya_Singhal_2015", relation="struck_down_free_speech")
        self.G.add_edge("IPC_497",          "Joseph_Shine_2018",  relation="struck_down_gender_equality")
        self.G.add_edge("IPC_377",          "Navtej_Johar_2018",  relation="read_down_consensual_sex")
        self.G.add_edge("IPC_124A",         "Vombatkere_2022",    relation="stayed_and_omitted_in_BNS")
        self.G.add_edge("IPC_303",          "Mithu_Punjab_1983",  relation="struck_down_mandatory_death")
        self.G.add_edge("Aadhaar_Act_S57",  "Puttaswamy_2018",    relation="struck_down_private_mandate")
        self.G.add_edge("Electoral_Bonds",  "ADR_v_UOI_2024",     relation="struck_down_right_to_know")

    def _build_section_node(self, act_name: str, section_num: str) -> str:
        canonical_act = normalize_act_name(act_name)
        clean_sec     = str(section_num).strip().replace(" ", "_")
        return f"{canonical_act}_{clean_sec}"

    def get_related_sections(self, act_name: str, section_num: str) -> List[Dict]:
        node = self._build_section_node(act_name, section_num)
        if not self.G.has_node(node):
            return []

        related = []
        for neighbor in self.G.neighbors(node):
            edge_data = self.G.get_edge_data(node, neighbor)
            relation  = edge_data.get("relation", "related_to")
            related.append({
                "source":   node,
                "target":   neighbor,
                "relation": relation,
                "detail":   edge_data
            })
        for predecessor in self.G.predecessors(node):
            edge_data = self.G.get_edge_data(predecessor, node)
            relation  = edge_data.get("relation", "related_to")
            related.append({
                "source":   predecessor,
                "target":   node,
                "relation": f"is_{relation}_of",
                "detail":   edge_data
            })
        return related

    def get_act_replacement(self, act_name: str) -> Dict:
        canonical = normalize_act_name(act_name)
        if not self.G.has_node(canonical):
            return {}
        for neighbor in self.G.neighbors(canonical):
            edge_data = self.G.get_edge_data(canonical, neighbor)
            if edge_data.get("relation") == "replaced_by":
                return {
                    "old_act":  canonical,
                    "new_act":  neighbor,
                    "date":     edge_data.get("date", "2024-07-01"),
                    "relation": "replaced_by"
                }
        return {}

    def get_act_status(self, act_name: str) -> str:
        replacement = self.get_act_replacement(act_name)
        if replacement:
            return "repealed"
        return "active"

    def get_constitutional_context(self, act_name: str) -> List[str]:
        canonical = normalize_act_name(act_name)
        context = []
        if not self.G.has_node(canonical):
            return context
        for pred in self.G.predecessors(canonical):
            edge_data = self.G.get_edge_data(pred, canonical)
            if "override" in edge_data.get("relation", ""):
                context.append(f"{pred} overrides {canonical} in constitutional conflict")
            elif edge_data.get("relation") == "governs":
                context.append(f"{pred} governs procedure under {canonical}")
        return context

    def get_procedure_chain(self, start_step: str) -> List[str]:
        if not self.G.has_node(start_step):
            return []
        chain = [start_step]
        current = start_step
        visited = {start_step}
        while True:
            next_steps = [
                n for n in self.G.neighbors(current)
                if self.G.get_edge_data(current, n).get("relation")
                in ["triggers", "leads_to", "next_step", "remedy_before_civil_court", "first_appeal", "appealable_in"]
                and n not in visited
            ]
            if not next_steps:
                break
            current = next_steps[0]
            visited.add(current)
            chain.append(current)
        return chain

    def get_struck_down_info(self, section_node: str) -> Dict:
        if not self.G.has_node(section_node):
            return {}
        for neighbor in self.G.neighbors(section_node):
            edge_data = self.G.get_edge_data(section_node, neighbor)
            relation  = edge_data.get("relation", "")
            if "struck_down" in relation or "read_down" in relation or "stay" in relation:
                return {
                    "section":   section_node,
                    "case":      neighbor,
                    "status":    relation
                }
        return {}

    def expand_context(self, layer2_results: List[Dict]) -> List[str]:
        flat_insights = []
        seen_acts     = set()
        seen_sections = set()
        seed_nodes    = []

        for res in layer2_results:
            raw_act     = res.get("act_name", "")
            raw_section = str(res.get("section_number", ""))
            canonical_act = normalize_act_name(raw_act)
            section_node  = self._build_section_node(canonical_act, raw_section)

            if canonical_act not in seen_acts:
                seen_acts.add(canonical_act)
                seed_nodes.append(canonical_act)
                repl = self.get_act_replacement(canonical_act)
                if repl:
                    flat_insights.append(
                        f"[LAW UPDATE] {repl['old_act']} has been replaced "
                        f"by {repl['new_act']} (effective {repl['date']}). "
                        f"Please refer to current legislation."
                    )
                const_ctx = self.get_constitutional_context(canonical_act)
                flat_insights.extend(const_ctx)

            if section_node not in seen_sections:
                seen_sections.add(section_node)
                seed_nodes.append(section_node)
                struck = self.get_struck_down_info(section_node)
                if struck:
                    flat_insights.append(
                        f"[STRUCK DOWN WARNING] {struck['section']} is {struck['status']} "
                        f"in {struck['case']}. It is no longer valid law."
                    )
                related = self.get_related_sections(canonical_act, raw_section)
                for rel in related:
                    flat_insights.append(
                        f"Related: {rel['source']} {rel['relation']} {rel['target']}"
                    )

        # ─── GNN MULTI-HOP PATHWAY DISCOVERY ───
        try:
            from gnn_engine import gnn_engine
            gnn_prompt = gnn_engine.format_pathways_for_prompt(seed_nodes)
            if gnn_prompt:
                flat_insights.append(gnn_prompt)
        except Exception as e:
            print(f"[Graph] GNN pathway discovery note: {e}")

        return flat_insights

# Singleton instance
legal_graph = LegalKnowledgeGraph()

if __name__ == "__main__":
    print(f"Total Graph Nodes: {legal_graph.G.number_of_nodes()}")
    print(f"Total Graph Edges: {legal_graph.G.number_of_edges()}")
