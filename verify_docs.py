"""
verify_docs.py
==============
Regression checks for the PROSE.

WHY THIS EXISTS
---------------
This project verifies everything except its own sentences, and that asymmetry
has now cost it twice.

The `make_fig2.py` incident is the sharper of the two: the text dumps in
`results/` were correct the whole time and only the *figure* was wrong - and
the figure is the artefact people actually read and the one least likely to be
re-derived. The documentation is in exactly the same position. `README.md`
carried "the feature table is 77 columns" for weeks after it became 171, and
a claim about richness columns being identical to four decimal places silently
went from true to false when the orbit features landed.

Nobody notices, because prose does not raise exceptions.

So: the same standard applied everywhere else in this project. Nothing here is
asserted; every numeric claim in the documents is checked against the artefact
that actually determines it - the registries, the cache metadata, the corpus
manifest. If a document and the code disagree, this file fails loudly.

WHAT IT CHECKS
--------------
  1.  Corpus size agrees across the manifest, the caches and the prose.
  2.  Feature totals and the tier split (45/50/74/2 = 171) match the registry.
  3.  Cumulative-by-radius counts (2/62/145/170, +1 at hop 4) match the registry.
  4.  Orbit accounting: 71 node orbits, 73 from ORCA, and the two exclusions
      are actually documented rather than left as an unexplained gap.
  5.  Every beta_c quoted in the prose matches that network's cache metadata.
  6.  The dynamical regime (multiple / n_sims / convention) is identical across
      every network, and the prose says "five" rather than "three".
  7.  A blocklist of strings that were true once and are now false.
  8.  (added 2026-09-12) The archive record docs/archive/phase6_record.md: every
      BEGIN...END block re-hashes to the SHA-256 in its own marker and to the
      sidecar results/phase6_doc_moves_20260912.json, so the 47 documents folded
      into it on 2026-09-12 stay byte-verifiable after their originals were deleted.
  9.  (added 2026-09-12) Every document path under docs/ or results/ and every
      relative markdown link in the documents and code resolves to a file that
      exists, and every `#rec-...` anchor into the record exists. Code files
      whose docstrings still carry pre-reorganisation paths are allow-listed
      from the sidecar's `deferred_code_rewrites` until the stage 1-4 queue
      drains (hash-bound modules are not edited while it runs); the check prints
      how many remain so the debt is visible on every run.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not parse English. It looks for specific numeric claims in specific
documents. A check here is cheap to add and only ever added *after* a claim has
actually gone stale - the blocklist in particular is a record of real mistakes,
not a style guide. Do not try to make this general; make it specific and
correct.

Run:  python verify_docs.py
"""
import json
import re
from pathlib import Path

import pandas as pd

# The orbit-exclusion rule is imported rather than restated, so the check
# cannot drift from the code it is checking.
from influence.graphlets import REDUNDANT_ORBITS

ROOT = Path(__file__).resolve().parent
DOCS = {
    "README.md": ROOT / "README.md",
    "HANDOFF.md": ROOT / "HANDOFF.md",
    "study_doc_v2.md": ROOT / "docs" / "study_doc_v2.md",
}

FAIL: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label:56s} {detail}")
    if not ok:
        FAIL.append(label)


# ---------------------------------------------------------------------------
# Ground truth, read from the artefacts rather than from memory
# ---------------------------------------------------------------------------

def load_truth() -> dict:
    """
    Everything the documents are allowed to claim, derived from the caches.

    Deliberately reads the REGISTRY rather than the feature CSV header: the
    registry is what `select_features` actually consults, so it is what decides
    which features a radius-r observer is given. A column present in the CSV but
    absent from the registry would never be selected, and counting the CSV would
    therefore overstate the table.
    """
    metas = {}
    for p in sorted(ROOT.glob("cache_meta_*.json")):
        tag = p.name[len("cache_meta_"):-len(".json")]
        metas[tag] = json.loads(p.read_text())

    registries = {}
    for p in sorted(ROOT.glob("cache_registry_*.csv")):
        tag = p.name[len("cache_registry_"):-len(".csv")]
        registries[tag] = pd.read_csv(p)

    # Sweeps are read RAW - deliberately not through analyse.load, which
    # de-duplicates. The point of check_no_duplicate_cells is to inspect what is
    # actually on disk; loading through the guard would hide exactly the defect
    # the check exists to find.
    sweeps = {}
    for p in sorted(ROOT.glob("sweep_*.csv")):
        tag = p.name[len("sweep_"):-len(".csv")]
        sweeps[tag] = pd.read_csv(p)

    manifest_path = ROOT / "data" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None

    return {"metas": metas, "registries": registries, "sweeps": sweeps,
            "manifest": manifest}


def registry_facts(reg: pd.DataFrame) -> dict:
    """Tier split, cumulative-by-radius counts and orbit counts for one network."""
    tier = reg["tier"].value_counts().to_dict()

    # Cumulative counts are what the "2 / 62 / 145 / 170" claim means: every
    # feature whose hop is <= r, which is exactly what select_features takes.
    cumulative = {r: int((reg["hop"] <= r).sum()) for r in range(0, 4)}

    node_orbits = reg[reg["feature"].str.startswith("orbit_")]
    edge_orbits = reg[reg["feature"].str.startswith("eorbit_")]

    return {
        "total": len(reg),
        "tier": {k: int(v) for k, v in tier.items()},
        "cumulative": cumulative,
        "above_max_hop": int((reg["hop"] > 3).sum()),
        "n_node_orbits": len(node_orbits),
        "n_edge_orbit_cols": len(edge_orbits),
        "node_orbit_by_hop": node_orbits["hop"].value_counts().sort_index().to_dict(),
    }


def read_docs() -> dict[str, str]:
    return {name: path.read_text(encoding="utf-8")
            for name, path in DOCS.items() if path.exists()}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_corpus_size(truth: dict, docs: dict[str, str]) -> None:
    """
    The corpus is whatever has a prepared cache. The prose must agree.

    This is check number one because it is the failure that keeps recurring:
    the corpus grew from three to five on 2026-08-27 and three separate
    documents went on saying "three networks" underneath a five-row table.
    """
    n_net = len(truth["metas"])
    print(f"\n[1] corpus size  (caches on disk: {n_net})")

    if truth["manifest"] is not None:
        # The manifest lists what was fetched; caches list what was prepared.
        # They can legitimately differ if something is downloaded but not yet
        # run, so this is reported rather than enforced.
        man_n = len(truth["manifest"]) if isinstance(truth["manifest"], (list, dict)) else "?"
        print(f"       manifest entries: {man_n} (informational)")

    # The stale phrasings, all of which were live in the documents on
    # 2026-08-28. Matched case-insensitively and word-bounded so that a
    # legitimate historical mention ("at three networks this read as...") is
    # not caught - those describe a past state and are correct.
    stale = [
        r"\bThree networks, all cleaned\b",
        r"\bAll three networks now run\b",
    ]
    for name, text in docs.items():
        for pat in stale:
            hits = re.findall(pat, text, flags=re.IGNORECASE)
            check(f"{name}: no '{pat[2:-2][:34]}'", not hits,
                  f"{len(hits)} hit(s)" if hits else "")


def check_feature_counts(truth: dict, docs: dict[str, str]) -> None:
    """
    Tier split and total, checked against the registry of every network.

    All five networks must agree with each other first - if they do not, the
    documents cannot possibly be right about all of them and the real bug is
    upstream in feature extraction, not in the prose.
    """
    facts = {tag: registry_facts(reg) for tag, reg in truth["registries"].items()}
    print("\n[2] feature counts")

    totals = {f["total"] for f in facts.values()}
    check("all networks have identical feature totals", len(totals) == 1,
          f"{sorted(totals)}")
    if len(totals) != 1:
        return

    total = totals.pop()
    ref = next(iter(facts.values()))
    tier = ref["tier"]
    print(f"       registry says: {total} total  "
          f"({tier.get('node')} node / {tier.get('edge')} edge / "
          f"{tier.get('subgraph')} subgraph / {tier.get('dynamic')} dynamic)")

    for name, text in docs.items():
        if "feature table is" not in text and "The 171 features" not in text:
            continue
        check(f"{name}: states {total} features", str(total) in text)
        for tname in ("node", "edge", "subgraph", "dynamic"):
            n = tier.get(tname)
            # Look for the count adjacent to its tier name, which is how both
            # the README paragraph and the HANDOFF table are written.
            near = re.search(rf"\b{n}\b[^\n|]{{0,24}}{tname}|{tname}[^\n|]{{0,24}}\|\s*{n}\b",
                             text)
            check(f"{name}: {tname} tier = {n}", near is not None)


def check_radius_ladder(truth: dict, docs: dict[str, str]) -> None:
    """The '2 at r=0, 62 at r=1, 145 at r=2, 170 at r=3' claim."""
    facts = {tag: registry_facts(reg) for tag, reg in truth["registries"].items()}
    print("\n[3] cumulative-by-radius ladder")

    ladders = {tuple(f["cumulative"][r] for r in range(4)) for f in facts.values()}
    check("all networks share one radius ladder", len(ladders) == 1, f"{sorted(ladders)}")
    if len(ladders) != 1:
        return

    ladder = ladders.pop()
    print(f"       registry says: r0={ladder[0]} r1={ladder[1]} "
          f"r2={ladder[2]} r3={ladder[3]}")

    ref = next(iter(facts.values()))
    check("exactly one feature sits above max_hop=3", ref["above_max_hop"] == 1,
          f"{ref['above_max_hop']}")

    for name, text in docs.items():
        if "Cumulative by radius" not in text:
            continue
        line = next(l for l in text.splitlines() if "Cumulative by radius" in l)
        for r, n in enumerate(ladder):
            check(f"{name}: ladder r={r} is {n}", str(n) in line, line[:44])


def check_orbit_accounting(truth: dict, docs: dict[str, str]) -> None:
    """
    Orbit counts, and - equally important - that the 73 -> 71 gap is EXPLAINED.

    This check exists because an external referee pulled on precisely this
    thread: ORCA emits 73 node orbits, the subgraph tier claims 71, and no
    document said which two were dropped or why. The answer was in the code all
    along (`REDUNDANT_ORBITS = (0, 3)`: orbit 0 is degree, orbit 3 is
    triangle_count) but a reader of the documents could not get to it.

    After the ORCA paw-orbit incident - where ORCA numbers the paw graphlet
    opposite to the obvious guess, and only a brute-force check caught it -
    orbit accounting is the last place this project should leave a gap.
    """
    facts = {tag: registry_facts(reg) for tag, reg in truth["registries"].items()}
    print("\n[4] orbit accounting")

    counts = {f["n_node_orbits"] for f in facts.values()}
    check("all networks have identical node-orbit counts", len(counts) == 1,
          f"{sorted(counts)}")
    if len(counts) != 1:
        return

    n_orb = counts.pop()
    ORCA_5NODE_ORBITS = 73          # fixed by ORCA (Hocevar-Demsar), not by us
    n_excluded = ORCA_5NODE_ORBITS - n_orb
    print(f"       registry says: {n_orb} node-orbit columns "
          f"({n_excluded} excluded from ORCA's {ORCA_5NODE_ORBITS})")

    for name, text in docs.items():
        if f"{n_orb} ORCA" not in text and f"**{n_orb}**" not in text:
            continue
        # The gap must be stated AND explained, not merely stated.
        check(f"{name}: names ORCA's true total ({ORCA_5NODE_ORBITS})",
              str(ORCA_5NODE_ORBITS) in text)
        explained = ("REDUNDANT_ORBITS" in text
                     or ("orbit 0" in text and "orbit 3" in text))
        check(f"{name}: explains the {ORCA_5NODE_ORBITS} -> {n_orb} exclusion",
              explained)

    # --- the 71 -> 70 step, which the 73 -> 71 answer did not cover ----------
    # `orbit_columns` also drops any orbit identically zero on a given graph.
    # That rule is real and would silently change the count per network, so the
    # documents' single "71" is only honest while it fires nowhere. Assert that,
    # rather than trusting a table written when it happened to be true.
    zero_skipped = {tag: (ORCA_5NODE_ORBITS - len(REDUNDANT_ORBITS)) - f["n_node_orbits"]
                    for tag, f in facts.items()}
    check("the all-zero orbit skip fires on no network",
          set(zero_skipped.values()) == {0},
          f"per-network orbits dropped as constant: {zero_skipped}")

    # Orbit 15 (induced-P5 endpoint) has eccentricity 4, so it is registered but
    # unreachable at MAX_HOP=3. That is the 171-vs-170 gap and the 71-vs-70 gap,
    # and it is the step an external review pulled on.
    ref = next(iter(facts.values()))
    check("exactly one orbit sits above MAX_HOP (71 registered, 70 selectable)",
          ref["above_max_hop"] == 1, f"{ref['above_max_hop']}")


def check_no_duplicate_cells(truth: dict) -> None:
    """
    No sweep CSV may contain the same (target, radius, richness, seed) twice.

    `stage2_sweep.py` appends per cell and resumes on the CSV, so an interrupted
    run can legitimately append a cell that a later run also writes. Every
    consumer goes through `analyse.load`, which de-duplicates - so this has
    never corrupted a published number - but "the guard downstream happens to
    hold" is not the same as "the artefact on disk is consistent", and any new
    script that reaches for `pd.read_csv` directly inherits the hazard. Four
    such rows were found in sweep_facebook_combined.csv on 2026-08-31.
    """
    print("\n[9] sweep-cell uniqueness")
    key = ["target", "radius", "richness", "seed"]
    for tag, sweep in sorted(truth["sweeps"].items()):
        dups = int(sweep.duplicated(key).sum())
        check(f"{tag}: no duplicated sweep cells", dups == 0,
              f"{dups} duplicate rows")


def check_beta_c(truth: dict, docs: dict[str, str]) -> None:
    """
    Every beta_c in the prose must match that network's cache metadata.

    Rounded to the precision the documents actually quote (5 decimal places).
    This is the check that would have caught the two missing rows: the HANDOFF
    listed three networks' thresholds while the corpus had five, so the single
    most load-bearing methodological claim in the project - that every network
    runs at the same multiple of its OWN threshold - was undocumented for the
    two networks that revised four findings.
    """
    print("\n[5] beta_c values")
    for tag, meta in sorted(truth["metas"].items()):
        bc = meta["beta_c"]
        quoted = f"{bc:.5f}"
        found_in = [name for name, text in docs.items() if quoted in text]
        check(f"beta_c {quoted} ({tag}) appears in a doc", bool(found_in),
              ", ".join(found_in) if found_in else "NOT DOCUMENTED ANYWHERE")


def check_regime(truth: dict, docs: dict[str, str]) -> None:
    """
    The dynamical regime must be identical across the whole corpus.

    email-Eu-core ran at 1.2x while the others ran at 1.5x once before, which
    silently reintroduced exactly the confound the beta_c normalisation exists
    to remove - and every cross-network finding was invalid while it lasted.
    That is a code-level check, not a prose one, but it belongs here because
    the prose asserts it in so many words.
    """
    print("\n[6] dynamical regime")
    metas = truth["metas"]

    for field in ("multiple", "n_sims", "convention"):
        vals = {m.get(field) for m in metas.values()}
        check(f"all networks share one '{field}'", len(vals) == 1, f"{sorted(map(str, vals))}")

    # p must actually equal multiple * beta_c on every network - the caches
    # could disagree with themselves and nothing else would notice.
    for tag, m in sorted(metas.items()):
        expect = m["multiple"] * m["beta_c"]
        ok = abs(m["p"] - expect) < 1e-12
        check(f"{tag}: p == multiple * beta_c", ok, f"{m['p']:.8f} vs {expect:.8f}")


# A stale claim being *quoted in order to correct it* is not a stale claim - it
# is this project's house style. Findings get revised in place with the old
# version kept visible ("REVISED A THIRD TIME", "Superseded framing, kept
# deliberately"), because a silent overwrite leaves a later reader unable to
# tell whether a change was noticed or merely forgotten.
#
# So the blocklist is matched PER LINE, and a line carrying one of these markers
# is exempt. The first version of this check was whole-document and immediately
# failed on the README's own correction note - which is the correct behaviour
# for a naive matcher and the wrong behaviour for this repository.
CORRECTION_MARKERS = (
    "earlier version", "previous version", "previously", "used to",
    "superseded", "stale", "was wrong", "no longer", "pre-ORCA",
)


def check_results_coverage(truth: dict, docs: dict[str, str]) -> None:
    """
    [8] Every headline results section must name every network in the corpus.

    This exists because of a specific failure found by hand on 2026-08-28. The
    study doc's section 17 opened with "All five networks ..." and then printed
    three tables; sections 18 and 19 did the same. The numbers in them were all
    current -- nothing was *wrong* -- but two of the five networks were simply
    absent, so a reader summing the tables would have concluded the corpus was
    three. That is invisible to every other check here, because each check
    validates a claim that IS made and none of them notices a claim that is
    missing.

    The check is deliberately crude: does the text of the section mention each
    network slug at all? It cannot tell a table from a passing reference, so it
    will not catch a network mentioned only in prose. It catches the failure
    mode that actually occurred -- a whole network silently absent from a
    section that claims to cover the corpus -- and nothing subtler. A stricter
    parse of the markdown tables was considered and rejected: the sections use
    several table shapes (per-network blocks in 17/18, one row per network in
    19), so a parser would have to know each one, and a check that needs
    updating whenever a table is reshaped is a check that gets disabled.

    Scoped to sections whose own header or intro claims corpus-wide coverage.
    A section explicitly labelled as covering fewer networks -- the r=1 subgraph
    ablation, the edge5 comparison -- is legitimately narrower and is not the
    target here.
    """
    networks = sorted(truth["metas"])
    doc = docs.get("study_doc_v2.md")
    if doc is None:
        return

    # Section boundaries: from a "## <n>." heading to the next one. Regex rather
    # than a markdown parser because these headings are the only level-2 rules
    # the document uses, and the numbering is stable.
    sections = re.split(r"\n(?=## \d+[a-z]?\. )", doc)
    index = {}
    for body in sections:
        m = re.match(r"## (\d+[a-z]?)\. ", body)
        if m:
            index[m.group(1)] = body

    # The three sections that state a corpus-wide scope in their own text.
    # Kept as an explicit list rather than detected from the prose: detecting
    # "all five networks" would make the check pass the moment someone deletes
    # that phrase, which is the wrong incentive.
    CORPUS_WIDE = {
        "17": "the locality budget curve",
        "18": "Finding 1 marginal gains",
        "19": "Finding 2 r*(eps)",
    }

    for num, what in CORPUS_WIDE.items():
        body = index.get(num)
        if body is None:
            check(f"study_doc section {num} present", False, f"missing: {what}")
            continue
        missing = [n for n in networks if n not in body]
        check(f"study_doc section {num} covers all {len(networks)} networks",
              not missing,
              f"{what}: absent = {', '.join(missing)}" if missing else "")


def check_blocklist(docs: dict[str, str]) -> None:
    """
    Strings that were true once and are now false.

    Every entry here is a real mistake that shipped, not a hypothetical. Add to
    this list whenever a claim goes stale - it costs one line and it is the
    cheapest guard in the project.
    """
    print("\n[7] known-stale strings")
    BLOCKED = [
        ("77 columns", "feature table was 77 columns pre-ORCA-5; it is 171"),
        ("two to five minutes", "sweep is 45-70 min/network, not 2-5 min"),
        ("45 node,\n14 edge", "pre-ORCA-5 tier split"),
        ("too large to process completely", "motivation is partial observability, not compute cost"),
        ("| `n_jobs` | 1 |", "n_jobs is -1 in experiment.py"),
    ]
    for name, text in docs.items():
        for needle, why in BLOCKED:
            if "\n" in needle:
                # Multi-line needles cannot be line-matched; check whole-text.
                offending = [needle] if needle in text else []
            else:
                offending = [
                    ln for ln in text.splitlines()
                    if needle in ln
                    and not any(mk in ln.lower() for mk in CORRECTION_MARKERS)
                ]
            check(f"{name}: no '{needle[:30]}'", not offending,
                  f"{why} (line: {offending[0][:38]!r})" if offending else "")


# ---------------------------------------------------------------------------

def check_c3_scored() -> None:
    """Guard the previously dangling 26i and its external-corpus/support claims.

    Check the actual table cells, not just a passing word in the report: a
    structural/shipped support substitution is small enough to hide in a verdict.
    """
    from scipy.stats import spearmanr
    from analyse_c3_benchmarks import REGIME

    graph = pd.read_csv(ROOT / 'results_c3_scored_graphs.csv').set_index('graph')
    cells = pd.read_csv(ROOT / 'results_c3_scored_cells.csv')
    study = (ROOT / 'docs/study_doc_v2.md').read_text(encoding='utf-8')
    prereg = (ROOT / 'docs/prereg/prereg_C3_benchmark_inflation.md').read_text(encoding='utf-8')
    section = study.split('## 26i.', 1)[-1].split('# PART VIII', 1)[0]
    scored = prereg.split('## SCORED', 1)[-1]
    check('C3: section 26i exists', '## 26i.' in study)
    check('C3: complete registered corpus', set(graph.index) == set(cells.graph) == set(REGIME))
    check('C3: row occurrence keys are unique', not cells.duplicated(['graph', 'algorithm', 'occurrence']).any())
    for name, row in graph.iterrows():
        observed = cells[cells.graph == name]
        hits = int((observed.tau_all <= observed.tau_floor + .05).sum())
        drop = observed['drop'].median()
        check(f'C3: {name} graph table matches cells',
              len(observed) == row.cells and hits == row.registered_hits
              and abs(drop - row.median_drop) < 1e-12)
        line = f'| {name} | {row.z:.6f} | {drop:.5f} | {hits}/{len(observed)} |'
        check(f'C3: {name} prose row agrees', line in section)
    rho = spearmanr(graph.z, graph.median_drop).statistic
    for title, text in [('26i', section), ('SCORED', scored)]:
        check(f'C3: {title} P2 measured rho', f'{rho:.6f}' in text)
        check(f'C3: {title} P1 absolute error', f'{cells.err.abs().median():.6f}' in text)
        check(f'C3: {title} P1 stays falsified', 'FALSIFIED' in text)
        check(f'C3: {title} clamped support stays explicit',
              all(f'{int(graph.loc[g, col]):,}' in text
                  for g in ['cit-Patents', 'com-lj']
                  for col in ['n_zero', 'n_zero_shipped']))
        check(f'C3: {title} P3 registered graph count',
              f'{int((graph.registered_hits > 0).sum())}/14' in text)


def check_multiplicity() -> None:
    """Pin study section 19b to results/multiplicity.csv (Task 6 finding P3-07).

    Added 2026-09-12 by Claude Opus 5. Three snapshots of the 19b table had
    drifted apart (the study, RESULTS_multiplicity.txt and make_fig6's
    docstring all carried different subgraph-tier counts), and the stated
    per-comparison alpha of the star rule was wrong (P3-01). This check reads
    the CSV the script writes, recomputes every number the section's CURRENT
    table quotes, and requires the exact table row to be present. It also
    requires that the captured stdout in RESULTS_multiplicity.txt carries the
    same summary, so the text file cannot silently go stale again.
    """
    import numpy as np
    from scipy.stats import t as t_dist

    csv = ROOT / 'results' / 'multiplicity.csv'
    txt = ROOT / 'results' / 'RESULTS_multiplicity.txt'
    check('19b: results/multiplicity.csv present', csv.is_file())
    check('19b: results/RESULTS_multiplicity.txt present', txt.is_file())
    if not (csv.is_file() and txt.is_file()):
        return
    d = pd.read_csv(csv)
    study = (ROOT / 'docs/study_doc_v2.md').read_text(encoding='utf-8')
    section = study.split('## 19b.', 1)[-1].split('\n## 20.', 1)[0]
    report = txt.read_text(encoding='utf-8')
    check('19b: section exists', '## 19b.' in study)
    check('19b: 240 comparisons in four families of 60',
          len(d) == 240 and d.family.value_counts().eq(60).all())

    # The star rule's real level: |t_(n-1)| > 2*sqrt(n), two-sided.
    alpha10 = 2.0 * t_dist.sf(2.0 * np.sqrt(10), 9)
    check('19b: states the star-rule alpha 1.37e-4 (not 0.046)',
          '1.37 × 10⁻⁴' in section and '|t₉| > 6.32' in section)
    # Every remaining "0.046" must sit inside a sentence that calls it wrong.
    stale = [m.start() for m in re.finditer(r'0\.046', section)]
    check('19b: "0.046" survives only as superseded wording',
          all(('Superseded' in section[max(0, i - 400):i]
               or 'P(|z| > 2)' in section[i:i + 400]) for i in stale),
          f'{len(stale)} occurrences')

    labels = {'hop_gain': 'hop gain (r→r+1)', 'edge_tier': 'edge tier',
              'subgraph_tier': 'subgraph tier', 'dynamic_tier': 'dynamic tier'}
    withdrawn_total = 0
    flat_report = ' '.join(report.split())
    for fam, label in labels.items():
        f = d[d.family == fam]
        stars = int(f.star.sum())
        exp_null = float((2.0 * t_dist.sf(2.0 * np.sqrt(f.n), f.n - 1)).sum())
        bh05 = int((f.q_bh < 0.05).sum())
        by05 = int((f.q_by < 0.05).sum())
        withdrawn = int((f.star & (f.q_bh >= 0.05)).sum())
        withdrawn_total += withdrawn
        row = (f'| {label} | {len(f)} | {stars} | {exp_null:.3f} | {bh05} | {by05} | '
               f'**{withdrawn}** |')
        # Detail kept ASCII: the console may be cp1252 and the label has an arrow.
        check(f'19b: current table row for {fam}', row in section,
              f'{stars} {exp_null:.3f} {bh05} {by05} {withdrawn}')
        # The script's SUMMARY block, whitespace-normalised so column padding
        # does not matter.
        summary = f'{fam} {len(f)} {stars} {exp_null:.4f} {bh05} {by05} {withdrawn}'
        check(f'19b: RESULTS_multiplicity.txt summary for {fam}',
              summary in flat_report, summary)
    # A star can never fail BH here (smallest BH threshold in a family of 60
    # at q=0.05 is 8.3e-4 > 1.37e-4): the CSV must agree with the theorem.
    check('19b: no star fails BH (holds by construction)', withdrawn_total == 0)
    check('19b: alpha at n=10 is below every BH threshold', alpha10 < 0.05 / 60)
    gained = int(((~d.star) & (d.q_bh < 0.05)).sum())
    check('19b: under-claimed count stated',
          f'{gained} across the four families' in section, str(gained))
    tiny = int((d.star & (d['mean'].abs() < 0.001)).sum())
    words = {12: 'Twelve', 13: 'Thirteen', 14: 'Fourteen', 15: 'Fifteen', 16: 'Sixteen'}
    check('19b: tiny-star count stated',
          f'{words.get(tiny, str(tiny))} starred comparisons' in section, str(tiny))
    check('19b: RESULTS_multiplicity.txt carries the corrected alpha line',
          'two-sided alpha = 1.4e-4' in report
          and 'expected under a global null  : 0.008' in report)


RECORD = ROOT / 'docs' / 'archive' / 'phase6_record.md'
MOVES = ROOT / 'results' / 'phase6_doc_moves_20260912.json'
# The marker the reorganisation script wrote; kept identical here so the two
# never disagree about what a block is.
BEGIN_RE = re.compile(rb'<!-- BEGIN (?P<path>\S+) sha256=(?P<sha>[0-9a-f]{64}) date=\S+ author=.*? -->\n')


def record_blocks(raw: bytes) -> dict[str, tuple[str, bytes]]:
    """old path -> (sha256 claimed by the marker, the block's bytes).

    A block is everything between the newline that ends its BEGIN marker line
    and the newline that starts its own END marker, so a file that ended without
    a trailing newline round-trips exactly.
    """
    out, pos = {}, 0
    while True:
        m = BEGIN_RE.search(raw, pos)
        if not m:
            return out
        path = m.group('path').decode()
        end = f'\n<!-- END {path} -->\n'.encode()
        j = raw.find(end, m.end())
        if j < 0:
            raise ValueError(f'record block {path} has no END marker')
        out[path] = (m.group('sha').decode(), raw[m.end():j])
        pos = j + len(end)


def check_record_integrity() -> None:
    """The archive record is verbatim by contract (Task 6 ledger paths are bound
    by SHA-256; deletion of the originals was safe only because the bytes are
    still here). Added 2026-09-12 by Claude Opus 5."""
    import hashlib
    print("\n[8] archive record: blocks re-hash to their markers")
    check('record: file present', RECORD.is_file())
    check('record: sidecar present', MOVES.is_file())
    if not (RECORD.is_file() and MOVES.is_file()):
        return
    blocks = record_blocks(RECORD.read_bytes())
    side = json.loads(MOVES.read_text(encoding='utf-8'))
    archived = {e['old_path']: e['sha256_original'] for e in side['entries'] if e['kind'] == 'archive'}
    check('record: block count matches the sidecar', set(blocks) == set(archived),
          f'{len(blocks)} blocks, {len(archived)} sidecar entries')
    bad = [p for p, (claimed, body) in blocks.items()
           if hashlib.sha256(body).hexdigest() != claimed or archived.get(p) != claimed]
    # Print every failing block, not a sample: the 2026-09-12 21:04 incident
    # (a whole-file edit flattened CRLF to LF inside nine blocks) was first
    # reported as three and cost time.
    check('record: every block re-hashes to its marker and the sidecar', not bad,
          ', '.join(bad))


def check_links_resolve() -> None:
    """Every document path in prose, code comments and markdown links points at a
    file that exists. Added 2026-09-12 by Claude Opus 5 after 47 files moved.

    Two exclusions, both deliberate: the record's own blocks (verbatim, links
    frozen as of 2026-09-12 — the whole file is skipped because its preamble
    quotes the old ledger path on purpose), and the code files listed in the
    sidecar's deferred_code_rewrites (hash-bound modules are not edited while
    the stage 1-4 queue runs). The deferred count is printed so the allow-list
    is never silently permanent.
    """
    print("\n[9] document paths and links resolve")
    side = json.loads(MOVES.read_text(encoding='utf-8')) if MOVES.is_file() else {}
    deferred = side.get('deferred_code_rewrites', {}).get('files', {})
    tok = re.compile(r'(?<![\w/])((?:docs|results)/[A-Za-z0-9_./-]+?\.md)(#[\w-]+)?')
    link = re.compile(r'\]\(([^)\s#]+\.md)(#[\w.-]+)?\)')
    record_text = RECORD.read_text(encoding='utf-8') if RECORD.is_file() else ''
    files = (list(ROOT.glob('*.md')) + [p for p in (ROOT / 'docs').rglob('*.md') if p != RECORD]
             + list((ROOT / 'results').glob('*.md')) + list(ROOT.glob('*.py'))
             + list((ROOT / 'influence').glob('*.py')) + list((ROOT / 'results').glob('*.ps1')))
    missing, bad_anchor, n_deferred = [], [], 0
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding='utf-8', errors='replace')
        for m in tok.finditer(text):
            path, frag = m.group(1), m.group(2)
            if rel in deferred and path in deferred[rel]:
                n_deferred += 1
                continue
            if not (ROOT / path).is_file():
                missing.append(f'{rel}: {path}')
            elif frag and path == 'docs/archive/phase6_record.md' and f'id="{frag[1:]}"' not in record_text:
                bad_anchor.append(f'{rel}: {frag}')
        if p.suffix == '.md':
            for m in link.finditer(text):
                target = m.group(1)
                if '://' in target:
                    continue
                base = ROOT if target.startswith(('docs/', 'results/')) else p.parent
                if not (base / target).is_file():
                    missing.append(f'{rel}: ]({target})')
    check('links: every docs/ and results/ .md path exists', not missing,
          '; '.join(missing[:4]) + (' ...' if len(missing) > 4 else ''))
    check('links: every #rec- anchor exists in the record', not bad_anchor, '; '.join(bad_anchor[:4]))
    print(f"        deferred code-comment paths still allow-listed: {n_deferred} "
          f"in {len(deferred)} files (clear after STAGE 4 LANES COMPLETE)")


def main() -> None:
    print("=" * 78)
    print("verify_docs - checking the prose against the artefacts")
    print("=" * 78)

    truth = load_truth()
    docs = read_docs()

    if not truth["metas"]:
        raise SystemExit("no cache_meta_*.json found - run stage1_prepare.py first")
    print(f"\nnetworks: {', '.join(sorted(truth['metas']))}")
    print(f"documents: {', '.join(sorted(docs))}")

    check_corpus_size(truth, docs)
    check_feature_counts(truth, docs)
    check_radius_ladder(truth, docs)
    check_orbit_accounting(truth, docs)
    check_beta_c(truth, docs)
    check_regime(truth, docs)
    check_results_coverage(truth, docs)
    check_no_duplicate_cells(truth)
    check_blocklist(docs)
    check_c3_scored()
    check_multiplicity()
    check_record_integrity()
    check_links_resolve()

    print("\n" + "=" * 78)
    if FAIL:
        print(f"FAILURES ({len(FAIL)}):")
        for f in FAIL:
            print("   -", f)
        raise SystemExit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
