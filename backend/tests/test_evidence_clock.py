"""Self-checks for the deterministic Section 138 clock in evidence_processor.

Run: python backend/tests/test_evidence_clock.py   (or pytest)
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from evidence_processor import _ground_statutory_clock, _parse_date  # noqa: E402

TODAY = datetime(2026, 11, 16)
MEMO = "CHEQUE RETURN MEMO\nDate of return: 02/11/2026\nCheque No: 448812  Date of cheque: 20/10/2026\nAmount: Rs. 2,00,000/-"
GOOD = {"category": "cheque_dishonour", "confidence_score": 0.9,
        "transaction_details": {"amount": "Rs. 2,00,000", "date": "20/10/2026"},
        "statutory_clock": {"bank_return_date": "today", "days_remaining": 650}}


def test_parse_date_formats():
    assert _parse_date("on 02/11/2026") == datetime(2026, 11, 2)
    assert _parse_date("2 November 2026") == datetime(2026, 11, 2)
    assert _parse_date("2nd Nov, 2026") == datetime(2026, 11, 2)
    assert _parse_date("no date here") is None
    assert _parse_date("31/02/2026") is None


def test_clock_uses_return_line_not_cheque_date():
    clock, conf = _ground_statutory_clock(GOOD, MEMO, TODAY)
    assert clock["bank_return_date"] == "02 November 2026"
    assert clock["notice_deadline"] == "02 December 2026"
    assert clock["days_remaining"] == 16 and clock["urgency_level"] == "STANDARD"
    assert conf == 0.9


def test_urgency_and_expiry():
    late = {**GOOD, "statutory_clock": {}}
    assert _ground_statutory_clock(late, "Returned on 01/11/2026", datetime(2026, 11, 26))[0]["urgency_level"] == "CRITICAL"
    assert _ground_statutory_clock(late, "Returned on 01/10/2026", TODAY)[0]["urgency_level"] == "EXPIRED"


def test_confidence_capped_when_nothing_read():
    guessed = {"category": "cheque_dishonour", "confidence_score": 0.95,
               "transaction_details": {"amount": None, "date": "Not visible"}, "statutory_clock": {}}
    clock, conf = _ground_statutory_clock(guessed, "", TODAY)
    assert conf <= 0.3 and clock["days_remaining"] is None and clock["notice_clock_active"] is False


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
