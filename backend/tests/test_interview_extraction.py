"""Self-checks for multi-fact interview answers (no network: LLM is stubbed).

Run: python backend/tests/test_interview_extraction.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import interview_state as ist  # noqa: E402


class _Stub:
    def __init__(self, reply): self.reply = reply
    def invoke(self, _prompt): return type("R", (), {"content": self.reply})()


def _run(reply, answers):
    ist._ensure_field_llm = lambda: _Stub(reply)
    st = ist.InterviewState()
    st.start_interview("cheque_bounce", "draft a cheque bounce notice", doc_family="letter",
                       dynamic_fields=ist.generate_field_questions("letter", "cheque_bounce", ""))
    out = ""
    for a in answers:
        out = st.record_answer(a)
    return st, out


def test_paragraph_fills_many_fields_and_skips_them():
    facts = "My name is Ramesh Kumar, 14 MG Road Bengaluru. The drawer is Suresh Patel, 22 Brigade Road. Cheque 448812 for Rs 2,00,000."
    st, out = _run('{"sender_name":"Ramesh Kumar","sender_address":"14 MG Road Bengaluru","recipient_name":"Suresh Patel",'
                   '"recipient_address":"22 Brigade Road","cheque_number":"448812","amount":"Rs 2,00,000","bogus":"x"}', [facts])
    assert st.collected["sender_name"] == "Ramesh Kumar"
    assert st.collected["recipient_name"] == "Suresh Patel"
    assert "bogus" not in st.collected
    assert "Date on Cheque" in out  # next unanswered field, skipping the six already filled


def test_short_answer_never_calls_llm():
    ist._ensure_field_llm = lambda: (_ for _ in ()).throw(AssertionError("LLM called"))
    st = ist.InterviewState()
    st.start_interview("cheque_bounce", "", doc_family="letter",
                       dynamic_fields=ist.generate_field_questions("letter", "cheque_bounce", ""))
    st.record_answer("Ramesh Kumar")
    assert st.collected == {"sender_name": "Ramesh Kumar"}


def test_bad_llm_output_falls_back_to_raw_answer():
    long_reply = "I am Ramesh Kumar and I live at 14 MG Road, Bengaluru, near the metro station, opposite the park."
    st, _ = _run("not json at all", [long_reply])
    assert st.collected["sender_name"] == long_reply


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("PASS", n)
