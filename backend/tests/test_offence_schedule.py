"""Self-checks for offence classification grounding. Run: python backend/tests/test_offence_schedule.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from offence_schedule import match_offences, schedule_notes  # noqa: E402


def test_cheating_question_gets_all_subsections():
    n = schedule_notes("What is the punishment for cheating under BNS 2023?")
    assert "s.318(4)" in n and "Cognizable; Non-bailable" in n and "s.318(2)" in n and "Non-cognizable; Bailable" in n


def test_named_sections_and_retrieval():
    assert match_offences("is section 318 bailable?") == ["BNS 318"]
    assert "NI Act 138" in match_offences("my cheque bounced, what can I do")
    assert match_offences("punishment", [{"act_name": "BNS", "section_number": "103"}]) == []  # retrieval alone is not enough
    assert match_offences("what does section 103 say", [{"act_name": "BNS", "section_number": "103"}]) == ["BNS 103"]


def test_unrelated_question_injects_nothing():
    assert schedule_notes("How do I register a rental agreement in Pune?") == ""


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("PASS", k)
