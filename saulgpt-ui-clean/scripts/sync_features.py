#!/usr/bin/env python3
"""
sync_features.py — keep the Clean UI's feature components identical to the
classic UI (saulgpt-ui) in behaviour, while re-skinning their colours.

What it does
------------
1. Copies the shared feature components (Trial Studio, Evidence uploader,
   Veto card, Toulmin matrix, …) from ../saulgpt-ui/src into src/features/.
   The JSX logic is copied byte-for-byte; only import paths are adjusted.
2. Rewrites every colour in the copied .css files so the dark
   "mahogany & gold" palette becomes the Clean UI's zinc + blue palette,
   expressed through CSS variables that flip automatically in light/dark mode.
3. Swaps the serif display fonts for Inter.

Run it whenever a feature component changes in the classic UI:

    python saulgpt-ui-clean/scripts/sync_features.py

The classic UI itself is never modified.
"""
import colorsys
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLEAN = HERE.parent
CLASSIC_SRC = CLEAN.parent / "saulgpt-ui" / "src"
DEST = CLEAN / "src" / "features"

FEATURE_FILES = [
    "TrialStudio.jsx", "TrialStudio.css",
    "EvidenceUploader.jsx", "EvidenceUploader.css",
    "VirtualBench.jsx", "VirtualBench.css",
    "VetoCard.jsx", "VetoCard.css",
    "ToulminMatrix.jsx", "ToulminMatrix.css",
    "DecodedTermsRibbon.jsx", "DecodedTermsRibbon.css",
    "LegalInfographic.jsx", "LegalInfographic.css",
    "AudioPillPlayer.jsx", "AudioPillPlayer.css",
    "BNSCorrectionNotice.jsx", "BNSCorrectionNotice.css",
    "UrgencyBanner.jsx", "UrgencyBanner.css",
    "JurisdictionBadge.jsx", "JurisdictionBadge.css",
    "LegalGlossary.js", "usePDF.js",
]

IMPORT_FIXES = [
    ('from "./apiConfig"', 'from "../apiConfig"'),
    ('from "./ApiKeyModal"', 'from "../components/ApiKeyModal"'),
]

# Small, behaviour-preserving JSX patches for the new layout.
# Each entry: file -> list of (exact original text, replacement).
# If the original text is not found (component changed upstream) the script
# warns and copies the file unpatched.
JSX_PATCHES = {
    "TrialStudio.jsx": [
        # Don't jump to the bottom of the (empty) chamber when the studio opens;
        # still auto-scroll as soon as the cross-examination starts.
        (
            'interrogationEndRef.current?.scrollIntoView({ behavior: "smooth" });\n  }, [turns, loading]);',
            'if (turns.length > 0 || loading) interrogationEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });\n  }, [turns, loading]);',
        ),
    ],
}

# Extra CSS appended to specific files after re-theming (small layout fixes
# for the new shell, e.g. Trial Studio living inside a panel, not full-screen).
CSS_APPENDIX = {
    "TrialStudio.css": """
/* ── Clean UI: Trial Studio lives inside the main panel ── */
.trial-studio-container { height: 100% !important; min-height: 0 !important; }
""",
}

TEXT_PROPS = {"color", "-webkit-text-fill-color", "caret-color", "text-decoration-color", "fill", "stroke"}
BG_PROPS = {"background", "background-color", "background-image"}

HEX_RE = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
RGB_RE = re.compile(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+%?)\s*)?\)")
NAMED_RE = re.compile(r"(?<![\w-])(white|black)(?![\w-])", re.I)
DECL_RE = re.compile(r"(?P<prop>[-a-zA-Z]+)\s*:\s*(?P<val>[^;{}]+)")


def parse_hex(h):
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return r, g, b, a


def tok(name, a):
    if a >= 0.999:
        return f"rgb(var(--t-{name}))"
    return f"rgb(var(--t-{name}) / {a:.3g})"


def is_saturated_solid(r, g, b, a):
    _, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return a >= 0.6 and s > 0.3 and 0.2 <= l < 0.85


def block_has_saturated_bg(body):
    for m in DECL_RE.finditer(body):
        if m.group("prop").lower() not in BG_PROPS:
            continue
        val = m.group("val")
        for hm in HEX_RE.finditer(val):
            if is_saturated_solid(*parse_hex(hm.group(0))):
                return True
        for rm in RGB_RE.finditer(val):
            a = rm.group(4)
            a = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
            if is_saturated_solid(float(rm.group(1)), float(rm.group(2)), float(rm.group(3)), a):
                return True
    return False


ON_SATURATED_BG = {"flag": False}
CLIP_TEXT = {"flag": False}  # block uses background-clip:text -> gradient is text colour


def map_color(r, g, b, a, prop):
    """Return a replacement CSS colour expression for (r,g,b,a) in `prop`."""
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    # Dark text sitting on a coloured button/badge -> white text on accent
    if prop in TEXT_PROPS and l < 0.3 and ON_SATURATED_BG["flag"]:
        return tok("on-accent", a)
    hue = h * 360
    is_text = prop in TEXT_PROPS
    is_bg = prop in BG_PROPS
    is_shadow = "shadow" in prop

    # Pure black shadows/overlays: keep (they read fine in both themes).
    if r < 8 and g < 8 and b < 8:
        if is_shadow or a < 0.999:
            return None
        return tok("fg", a) if is_text else tok("bg", a)

    slate = 195 <= hue <= 235 and s < 0.5 and (l < 0.3 or l > 0.55)
    gold = 28 <= hue <= 58 and s > 0.3 and 0.25 <= l < 0.85
    neutral = s < 0.22 or slate or l < 0.2 or (l >= 0.85 and 25 <= hue <= 60)

    if gold and not neutral:
        if is_shadow:
            return tok("accent", min(a, 0.35))
        return tok("accent-strong" if (is_text and l > 0.6) else "accent", a)

    if neutral:
        if is_shadow:
            return None if l < 0.3 else tok("ink", min(a, 0.12))
        if is_text:
            if l >= 0.88:
                return tok("fg", a)
            if l >= 0.7:
                return tok("fg2", a)
            if l >= 0.45:
                return tok("muted", a)
            return tok("faint", a)
        # backgrounds / borders / misc
        if l < 0.12:
            return tok("bg", a)
        if l < 0.3:
            return tok("surface", a) if a >= 0.6 else tok("surface2", a)
        if l < 0.55:
            return tok("surface2", a) if is_bg else tok("ink", min(a, 0.2) if a < 1 else 0.18)
        # light neutrals used as tints/hairlines on the old dark UI
        if a < 0.999:
            return tok("ink", a)
        return tok("surface", 1) if is_bg else tok("ink", 0.15)

    # Saturated semantic colours (red/green/sky …): keep the hue but make
    # light pastel *text* readable on light backgrounds.
    if is_text and l > 0.6:
        hexv = f"#{r:02x}{g:02x}{b:02x}"
        pct = 55
        base = f"color-mix(in srgb, {hexv} {pct}%, rgb(var(--t-fg)))"
        return base if a >= 0.999 else f"color-mix(in srgb, {base} {int(a*100)}%, transparent)"
    return None


def transform_value(prop, val):
    if CLIP_TEXT["flag"] and prop in BG_PROPS:
        prop = "color"
    def sub_hex(m):
        r, g, b, a = parse_hex(m.group(0))
        rep = map_color(r, g, b, a, prop)
        return rep if rep else m.group(0)

    def sub_rgb(m):
        r, g, b = (float(m.group(i)) for i in (1, 2, 3))
        a = m.group(4)
        a = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        rep = map_color(r, g, b, a, prop)
        return rep if rep else m.group(0)

    def sub_named(m):
        w = m.group(1).lower()
        rgb = (255, 255, 255) if w == "white" else (0, 0, 0)
        rep = map_color(*rgb, 1.0, prop)
        return rep if rep else m.group(0)

    val = HEX_RE.sub(sub_hex, val)
    val = RGB_RE.sub(sub_rgb, val)
    if prop in TEXT_PROPS | BG_PROPS or prop.startswith("border"):
        val = NAMED_RE.sub(sub_named, val)
    return val


def transform_css(css):
    # Strip @import of the old serif fonts
    css = re.sub(r"@import\s+url\([^)]*fonts\.googleapis[^)]*\);?", "", css)

    def sub_decl(m):
        prop, val = m.group("prop").lower(), m.group("val")
        if prop.startswith("--"):
            return m.group(0)
        if prop == "font-family":
            low = val.lower()
            if "mono" in low or "courier" in low:
                return f"{m.group('prop')}: var(--font-mono)"
            return f"{m.group('prop')}: var(--font-body)"
        return f"{m.group('prop')}: {transform_value(prop, val)}"

    def rewrite_body(body):
        ON_SATURATED_BG["flag"] = block_has_saturated_bg(body)
        CLIP_TEXT["flag"] = bool(re.search(r"background-clip\s*:\s*text", body))
        try:
            return DECL_RE.sub(sub_decl, body)
        finally:
            ON_SATURATED_BG["flag"] = False
            CLIP_TEXT["flag"] = False

    # Only rewrite declarations inside rule bodies (skip selectors like a:hover)
    out, depth, i, buf = [], 0, 0, []
    for ch in css:
        if ch == "{":
            if depth >= 1:
                out.append(rewrite_body("".join(buf)))
            else:
                out.append("".join(buf))
            buf = []
            out.append(ch)
            depth += 1
        elif ch == "}":
            out.append(rewrite_body("".join(buf)) if depth >= 1 else "".join(buf))
            buf = []
            out.append(ch)
            depth = max(0, depth - 1)
        else:
            buf.append(ch)
    out.append("".join(buf))
    return "".join(out)


def main():
    if not CLASSIC_SRC.exists():
        sys.exit(f"Classic UI not found at {CLASSIC_SRC}")
    DEST.mkdir(parents=True, exist_ok=True)
    for name in FEATURE_FILES:
        src = CLASSIC_SRC / name
        if not src.exists():
            print(f"  skip (missing) {name}")
            continue
        text = src.read_text(encoding="utf-8-sig")
        if name.endswith((".jsx", ".js")):
            for a, b in IMPORT_FIXES:
                text = text.replace(a, b)
            for a, b in JSX_PATCHES.get(name, []):
                if a in text:
                    text = text.replace(a, b)
                else:
                    print(f"  WARNING: patch not applied to {name} (source changed): {a[:60]}...")
        elif name.endswith(".css"):
            text = "/* AUTO-GENERATED by scripts/sync_features.py from saulgpt-ui/src/" + name + \
                   " — edit the original, then re-run the script. */\n" + transform_css(text)
            text += CSS_APPENDIX.get(name, "")
        (DEST / name).write_text(text, encoding="utf-8")
        print(f"  synced {name}")
    print("Done.")


if __name__ == "__main__":
    main()
