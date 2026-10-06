"""Render study_doc_v2.md -> study_document.pdf via markdown + weasyprint.

Paths resolve relative to THIS FILE (docs/), not to a hard-coded /home/claude
or to the cwd - changed 2026-09-12 by Claude Opus 5, Task 6 finding P3-03. The
script used to be runnable only inside the sandbox that first produced the PDF.

STALENESS NOTE (P3-03). `docs/study_document.pdf` was last built on 2026-08-18
and has not been rebuilt since: it predates every Phase 5/6 section of
study_doc_v2.md (sections 24.x, 26a-26k, the 19b revision, the C3/C4 lanes) and
the reader should treat the markdown as the document of record. weasyprint is
not installed in the `influence` conda environment (deliberately: it pulls
cairo/pango wheels that are not part of environment.yml), so the PDF is
rebuilt on demand in a separate environment with
    pip install markdown weasyprint
and run from anywhere as  python docs/build_study.py . Until that is done the
PDF stays labelled stale in HANDOFF.md.
"""
import re
from pathlib import Path

import markdown
from weasyprint import HTML, CSS

HERE = Path(__file__).resolve().parent
SRC_MD = HERE / "study_doc_v2.md"
OUT_HTML = HERE / "study_doc.html"
OUT_PDF = HERE / "study_document.pdf"
STYLE = HERE / "study.css"

md_src = SRC_MD.read_text(encoding="utf-8")

# Strip the leading title lines; we render them as a styled title block.
lines = md_src.split("\n")
title = lines[0].lstrip("# ").strip()
subtitle = lines[1].lstrip("# ").strip() if len(lines) > 1 else ""
rest = "\n".join(lines[2:])

html_body = markdown.markdown(
    rest,
    extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
)

# Convert ```math fenced blocks (rendered as <pre><code class="language-math">)
# into styled .math-block divs.
def math_repl(m):
    inner = m.group(1)
    # unescape entities markdown produced
    inner = (inner.replace("&amp;", "&").replace("&lt;", "<")
                  .replace("&gt;", ">").replace("&quot;", '"'))
    # x_{abc} and x_abc -> real subscripts; x^4 -> superscript
    inner = re.sub(r'_\{([^}]+)\}', r'<sub>\1</sub>', inner)
    inner = re.sub(r'_([A-Za-z0-9]+)', r'<sub>\1</sub>', inner)
    inner = re.sub(r'\^(\d)', r'<sup>\1</sup>', inner)
    return f'<div class="math-block">{inner}</div>'

html_body = re.sub(
    r'<pre><code class="language-math">(.*?)</code></pre>',
    math_repl, html_body, flags=re.S,
)
# fallback if the class isn't attached
html_body = re.sub(
    r'<pre><code>(\s*(?:b\(v\)|σ|τ|r\*|Δ|g_r|CV|SE|P@k)[^<]*?)</code></pre>',
    math_repl, html_body, flags=re.S,
)

# Subscripts inside ordinary prose and tables. Markdown leaves things like
# "beta_c" and "sigma_st" as literal underscores, which look like typos.
# We convert a conservative whitelist of known symbol_subscript patterns so we
# never accidentally mangle a filename or an identifier such as
# collective_influence_2.
SUBSCRIPT_PATTERNS = [
    (r'β_c', 'β<sub>c</sub>'),
    (r'σ_st\(v\)', 'σ<sub>st</sub>(v)'),
    (r'σ_st', 'σ<sub>st</sub>'),
    (r'λ₁', 'λ<sub>1</sub>'),
    (r'\bk_i\b', 'k<sub>i</sub>'),
    (r'\bk_j\b', 'k<sub>j</sub>'),
    (r'\bn_c\b', 'n<sub>c</sub>'),
    (r'\bn_d\b', 'n<sub>d</sub>'),
    (r'\bb_r\(v\)', 'b<sub>r</sub>(v)'),
    (r'\bg_r\(v\)', 'g<sub>r</sub>(v)'),
    (r'\bg_r\b', 'g<sub>r</sub>'),
    (r'\bR_m\(i\)', 'R<sub>m</sub>(i)'),
    (r'\bε_i\b', 'ε<sub>i</sub>'),
    (r'\bh⁽ⁿ⁾', 'h<sup>(n)</sup>'),
    (r'CI_ℓ', 'CI<sub>ℓ</sub>'),
    (r'p_uv', 'p<sub>uv</sub>'),
    (r'τ_local', 'τ<sub>local</sub>'),
    (r'τ_recompute', 'τ<sub>recompute</sub>'),
    (r'shell_r_count', '<code>shell_r_count</code>'),
]

def apply_subscripts(html: str) -> str:
    """Apply the whitelist outside of <code>/<pre> regions."""
    parts = re.split(r'(<code>.*?</code>|<pre>.*?</pre>)', html, flags=re.S)
    for idx in range(0, len(parts), 2):          # even indices = outside code
        for pat, rep in SUBSCRIPT_PATTERNS:
            parts[idx] = re.sub(pat, rep, parts[idx])
    return "".join(parts)

html_body = apply_subscripts(html_body)

title_block = (
    f'<h1 class="doctitle">{title}</h1>'
    f'<div class="docsub">{subtitle}</div>'
    f'<div class="docmeta">Working reference for the project team</div>'
)

full = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body>{title_block}{html_body}</body></html>"""

OUT_HTML.write_text(full, encoding="utf-8")

HTML(string=full, base_url=str(HERE)).write_pdf(
    str(OUT_PDF),
    stylesheets=[CSS(filename=str(STYLE))],
)
print(f"built {OUT_PDF}")
