"""
Offence classification facts (BNSS 2023, First Schedule; NI Act for s.138).

The law database holds section TEXT only, not whether an offence is cognizable/bailable or its
maximum punishment, so the answer model used to guess (e.g. calling all cheating "non-cognizable
and bailable", which is wrong for s.318(4)). These facts are injected into the prompt when a
question touches one of these offences. Keep entries to what is certain; when in doubt leave a
section out (the prompt then tells the model to say the classification depends on the subsection).
"""
import re
from typing import Iterable, List

# key -> (title, [(provision, punishment, cognizable, bailable)], trigger words)
SCHEDULE = {
    "BNS 318": ("Cheating", [
        ("s.318(2) cheating", "up to 3 years, or fine, or both", "Non-cognizable", "Bailable"),
        ("s.318(3) cheating a person whose interest the offender was bound to protect", "up to 5 years, or fine, or both", "Non-cognizable", "Bailable"),
        ("s.318(4) cheating and dishonestly inducing delivery of property (old IPC 420)", "up to 7 years and fine", "Cognizable", "Non-bailable"),
    ], ("cheating", "cheat", "fraud", "420")),
    "BNS 316": ("Criminal breach of trust", [
        ("s.316(2)", "up to 5 years, or fine, or both", "Cognizable", "Non-bailable"),
    ], ("breach of trust", "406")),
    "BNS 303": ("Theft", [
        ("s.303(2)", "up to 3 years, or fine, or both (community service possible for a first theft under Rs 5,000 when the property is returned)", "Cognizable", "Non-bailable"),
    ], ("theft", "stolen", "379")),
    "BNS 308": ("Extortion", [
        ("s.308(2)", "up to 7 years, or fine, or both", "Cognizable", "Non-bailable"),
    ], ("extortion", "384")),
    "BNS 356": ("Defamation", [
        ("s.356(2)", "simple imprisonment up to 2 years, or fine, or both, or community service", "Non-cognizable", "Bailable"),
    ], ("defamation", "defame", "500")),
    "BNS 115": ("Voluntarily causing hurt", [
        ("s.115(2)", "up to 1 year, or fine up to Rs 10,000, or both", "Non-cognizable", "Bailable"),
    ], ("causing hurt", "slapped", "beat me", "assaulted", "323")),
    "BNS 85": ("Cruelty by husband or his relatives (old IPC 498A)", [
        ("s.85", "up to 3 years and fine", "Cognizable", "Non-bailable"),
    ], ("cruelty", "498a", "harassment by husband", "in-laws")),
    "BNS 80": ("Dowry death", [
        ("s.80(2)", "not less than 7 years, up to life imprisonment", "Cognizable", "Non-bailable"),
    ], ("dowry death",)),
    "BNS 103": ("Murder", [
        ("s.103(1)", "death or imprisonment for life, and fine", "Cognizable", "Non-bailable"),
    ], ("murder", "302")),
    "BNS 64": ("Rape", [
        ("s.64(1)", "rigorous imprisonment not less than 10 years, up to life, and fine", "Cognizable", "Non-bailable"),
    ], ("rape", "376")),
    "BNS 74": ("Assault or criminal force to outrage a woman's modesty (old IPC 354)", [
        ("s.74", "1 to 5 years and fine", "Cognizable", "Non-bailable"),
    ], ("outrage", "modesty", "molest", "354")),
    "BNS 329": ("Criminal trespass", [
        ("s.329(3)", "up to 3 months, or fine up to Rs 5,000, or both", "Cognizable", "Bailable"),
    ], ("trespass", "447")),
    "NI Act 138": ("Dishonour of cheque", [
        ("s.138 Negotiable Instruments Act", "up to 2 years, or fine up to twice the cheque amount, or both", "Non-cognizable (court takes it up only on a written complaint, s.142)", "Bailable; compoundable (s.147)"),
    ], ("cheque bounce", "bounced cheque", "dishonour", "dishonor", "cheque return", "section 138", "s.138", "138 ni")),
}

_SEC = re.compile(r"\b(?:section|sec\.?|s\.)\s*(\d{1,3})\b", re.I)


def match_offences(query: str, retrieved: Iterable[dict] = ()) -> List[str]:
    """Schedule keys relevant to the question (words in the question, or sections it names or retrieval returned)."""
    q = (query or "").lower()
    named = set(_SEC.findall(q))
    for d in retrieved or ():
        if isinstance(d, dict) and "BNS" in str(d.get("act_name", "")).upper():
            named.add(str(d.get("section_number", "")).strip())
    keys = []
    for key, (_, _, words) in SCHEDULE.items():
        num = key.split()[-1]
        if any(w in q for w in words) or (key.startswith("BNS") and num in named and re.search(rf"\b{num}\b", q)):
            keys.append(key)
    return keys[:3]


def schedule_notes(query: str, retrieved: Iterable[dict] = ()) -> str:
    """Prompt block with the official classification for offences the question is about ('' if none)."""
    keys = match_offences(query, retrieved)
    if not keys:
        return ""
    lines = ["--- OFFICIAL CLASSIFICATION (BNSS 2023 First Schedule; NI Act) ---",
             "Use these facts exactly. Where subsections differ, name the subsection; never say 'generally'.",
             "'up to N years' is a MAXIMUM: never present it as a range with a minimum unless one is stated."]
    for key in keys:
        title, rows, _ = SCHEDULE[key]
        lines.append(f"{key} - {title}:")
        lines += [f"  * {p}: punishment {pun}; {cog}; {bail}." for p, pun, cog, bail in rows]
    lines.append("--- END OFFICIAL CLASSIFICATION ---")
    return "\n".join(lines)
