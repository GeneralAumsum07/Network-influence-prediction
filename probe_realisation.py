"""L6 realisation-noise calibration (prereg 2026-11-02 23:30, "L6 realisation-noise calibration").

L6 measured sd_g across fitting seeds on ONE graph per gamma, so its noise
yardstick never saw graph-to-graph variation. This run regenerates the gamma
family with generator seeds 1-3 and fits three of its gammas exactly as L6's
primary arm did, so seed 0 (L6's graph) plus these give 4 realisations per gamma.
It is a calibration: nothing here is scored, and L6's FLAT stands regardless.

  prepare  stage 0 per seed into data/synthetic/s<k>/ (git-ignored, so the
           sha256 of each list goes into realisations/corpus.json), the LCC
           size and NB gap per fitted graph, then stage 1 per graph with
           cwd=realisations/s<k>/. The tags are L6's own (stage 0 does not put
           the seed in the name), which is why each seed gets its own cwd:
           one shared directory would overwrite caches across seeds.
  fit      stage 2 spread_mean / rf, radii 0-3, 5 seeds, per graph. Resumable.
  analyse  the part D numbers -> realisations/calibration.json.

Run from the repo root:
  python probe_realisation.py prepare | fit | analyse
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from influence.experiment import TIER_LADDER
from influence.nb_spectrum import nb_spectral_gap
from influence.preprocessing import load_edgelist
from probe_beta_sweep import local_imports, reconcile_refits, run_stage, take_lock
from probe_certificate import (MAX_HOP, MULTIPLE, CONVENTION, N_SEEDS, N_SIMS,
                               OUT as L6_OUT)
from probe_threshold_arm import sha256, write_atomic

ROOT = Path(__file__).resolve().parent
OUT = L6_OUT / "realisations"
LOCK = OUT / "active.lock"
GEN_SEEDS = (1, 2, 3)
# Part B: only the two ends and the dip of L6's family are fitted.
GAMMAS = (2.1, 3.0, 4.0)
TIER = "node+edge+subgraph"


def tag(g: float) -> str:
    return f"CL_n5000_g{g:g}_k6"


def syn_dir(k: int) -> Path:
    # Under data/synthetic/, which .gitignore already covers, and outside the
    # seed-0 files L6's sources.json pins, so L6's guard is untouched.
    return Path("data/synthetic") / f"s{k}"


def run_dir(k: int) -> Path:
    return OUT / f"s{k}"


def log(message: str) -> None:
    from datetime import datetime
    line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}"
    print(line, flush=True)
    with (OUT / "controller.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def units() -> list[tuple[int, float]]:
    return [(k, g) for k in GEN_SEEDS for g in GAMMAS]


def pinned_files() -> list[Path]:
    """Repo files that decide a number here: the stage scripts' imports plus every fitted list."""
    files = set()
    for entry in ("stage1_prepare.py", "stage2_sweep.py"):
        files |= {p.relative_to(ROOT) for p in local_imports(ROOT / entry)}
    files |= {syn_dir(k) / f"{tag(g)}.txt" for k, g in units()}
    return sorted(files)


def current_sources() -> dict[str, str]:
    return {p.as_posix(): sha256(ROOT / p) for p in pinned_files()}


def check_sources() -> None:
    recorded = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
    current = current_sources()
    changed = sorted(k for k in recorded.keys() | current.keys()
                     if recorded.get(k) != current.get(k))
    if changed:
        raise RuntimeError(f"pinned inputs changed since prepare: {changed}; refusing")


def stage1_done(k: int, g: float) -> bool:
    d, t = run_dir(k), tag(g)
    names = [f"cache_{kind}_{t}.csv" for kind in ("features", "targets", "registry")]
    meta = d / f"cache_meta_{t}.json"
    if not (meta.is_file() and all((d / n).is_file() for n in names)):
        return False
    m = json.loads(meta.read_text(encoding="utf-8"))
    return (m["n_sims"], m["multiple"], m["convention"], m["max_hop"]) == \
        (N_SIMS, MULTIPLE, CONVENTION, MAX_HOP)


def fit_done(k: int, g: float) -> tuple[bool, str]:
    """Same completeness rule as probe_certificate.arm_done, for the spread arm only."""
    d, t = run_dir(k), tag(g)
    sweep, oof = d / f"sweep_{t}.csv", d / f"cache_oof_{t}.npz"
    if not (sweep.exists() and oof.exists()):
        return False, "no sweep yet"
    df = pd.read_csv(sweep)
    keys = [(r.target, int(r.radius), r.richness, int(r.seed)) for r in df.itertuples()]
    want = {("spread_mean", r, rung, s) for r in range(MAX_HOP + 1)
            for rung in TIER_LADDER for s in range(N_SEEDS)}
    if len(keys) != len(set(keys)) or set(keys) != want:
        return False, f"{len(want - set(keys))} missing, {len(keys) - len(set(keys))} duplicate"
    with np.load(oof) as store:
        if any("|".join(map(str, key)) not in store.files for key in want):
            return False, "OOF predictions missing"
    return True, f"{len(want)} cells"


def run_prepare() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    corpus = {"registered_in": "prereg 2026-11-02 23:30 L6 realisation-noise calibration, part B",
              "graphs": {}}
    for k in GEN_SEEDS:
        if not all((syn_dir(k) / f"{tag(g)}.txt").is_file() for g in GAMMAS):
            # Stage 0 is run unmodified; its output goes to a log, not the console.
            with (OUT / f"stage0_s{k}.out.log").open("w", encoding="utf-8") as fh:
                subprocess.run([sys.executable, "stage0_generate.py", "--n", "5000",
                                "--families", "gamma", "--seed", str(k), "--bootstrap", "200",
                                "--out", syn_dir(k).as_posix()],
                               cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, check=True)
        manifest = {Path(r["path"]).stem: r for r in
                    json.loads((syn_dir(k) / "manifest.json").read_text(encoding="utf-8"))}
        for g in GAMMAS:
            path = syn_dir(k) / f"{tag(g)}.txt"
            net = load_edgelist(str(path))
            row = {key: v for key, v in manifest[tag(g)].items() if key != "path"}
            corpus["graphs"][f"s{k}/{tag(g)}"] = {
                "gen_seed": k, "gamma_target": g, "edge_list": path.as_posix(),
                "edge_list_sha256": sha256(path), "stage0_profile": row,
                "lcc_n": int(net.n), "lcc_m": int(net.m),
                "lcc_mean_degree": float(net.mean_degree), **nb_spectral_gap(net)}
            c = corpus["graphs"][f"s{k}/{tag(g)}"]
            print(f"s{k} {tag(g):18s} lcc n={c['lcc_n']:5d} <k>={c['lcc_mean_degree']:.2f} "
                  f"gap={c['nb_spectral_gap']:.4f}", flush=True)
    write_atomic(OUT / "corpus.json", json.dumps(corpus, indent=2, default=str) + "\n")

    for k, g in units():
        run_dir(k).mkdir(parents=True, exist_ok=True)
        if stage1_done(k, g):
            continue
        # The edge list is passed relative to the cwd, so cache_meta records no machine path.
        rel = Path(os.path.relpath(ROOT / syn_dir(k) / f"{tag(g)}.txt", ROOT / run_dir(k))).as_posix()
        secs = run_stage("stage1", [str(ROOT / "stage1_prepare.py"), rel, str(N_SIMS),
                                    str(MULTIPLE), CONVENTION], run_dir(k), tag(g))
        if not stage1_done(k, g):
            raise RuntimeError(f"stage1 s{k} {tag(g)} exited 0 without its caches")
        print(f"stage1 s{k} {tag(g)} {secs:.0f}s", flush=True)
    write_atomic(OUT / "sources.json", json.dumps(current_sources(), indent=2) + "\n")
    print("wrote corpus.json and sources.json")
    return 0


def run_fit() -> int:
    if not all(stage1_done(k, g) for k, g in units()):
        raise SystemExit("run prepare first: a stage-1 cache is missing")
    log(f"START fit pid={os.getpid()} {take_lock(LOCK)}")
    ok = False
    try:
        for k, g in units():
            check_sources()        # before every graph: an edit mid-run stops the next fit
            done, why = fit_done(k, g)
            if done:
                log(f"SKIP s{k} {tag(g)} already complete ({why})")
                continue
            log(f"BEGIN s{k} {tag(g)}")
            secs = run_stage("stage2_spread_mean", [str(ROOT / "stage2_sweep.py"), tag(g),
                                                    "spread_mean", str(MAX_HOP), str(N_SEEDS), "rf"],
                             run_dir(k), tag(g))
            removed, worst = reconcile_refits(run_dir(k), tag(g))
            if removed:
                log(f"  reconciled s{k} {tag(g)}: {removed} stale row(s) (largest diff {worst:.3g})")
            done, why = fit_done(k, g)
            if not done:
                raise RuntimeError(f"stage2 s{k} {tag(g)} exited 0 but is incomplete: {why}")
            log(f"COMPLETE s{k} {tag(g)} ({why}; stage2 {secs:.0f}s)")
        ok = True
        log(f"ALL GRAPHS COMPLETE ({len(units())})")
    except Exception as exc:
        log(f"FAILED {exc}")
        raise
    finally:
        LOCK.unlink(missing_ok=True)
    return 0 if ok else 1


def rho_per_seed(sweep: Path) -> pd.Series:
    """tau1/tau3 per fitting seed, exactly as analyse_certificate.ratio_row forms it."""
    df = pd.read_csv(sweep)
    sub = df[(df.target == "spread_mean") & (df.richness == TIER)]
    tau = sub.pivot_table(index="seed", columns="radius", values="kendall_tau")
    return tau[1] / tau[3]


def run_analyse() -> int:
    if not all(fit_done(k, g)[0] for k, g in units()):
        raise SystemExit("refusing: a fit is incomplete")
    l6 = json.loads((L6_OUT / "corpus.json").read_text(encoding="utf-8"))["graphs"]
    rep = json.loads((OUT / "corpus.json").read_text(encoding="utf-8"))["graphs"]
    rows = []
    for k in (0, *GEN_SEEDS):
        for g in GAMMAS:
            # k = 0 is L6's own graph and sweep, read in place, not refitted.
            sweep = L6_OUT / f"sweep_{tag(g)}.csv" if k == 0 else run_dir(k) / f"sweep_{tag(g)}.csv"
            c = l6[tag(g)] if k == 0 else rep[f"s{k}/{tag(g)}"]
            r = rho_per_seed(sweep)
            rows.append({"gen_seed": k, "gamma_target": g, "rho": r.mean(), "rho_sd_fit": r.std(ddof=1),
                         "lcc_n": c["lcc_n"], "lcc_mean_degree": c["lcc_mean_degree"],
                         "nb_spectral_gap": c["nb_spectral_gap"]})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "rho_by_realisation.csv", index=False)

    # 1. Realisation sd against fitting sd (part D.1).
    s = df.groupby("gamma_target").rho.std(ddof=1)
    sd_real = float(np.sqrt((s ** 2).mean()))
    sd_fit = float(np.sqrt((df.rho_sd_fit ** 2).mean()))
    # 2. L6's end gap with realisation means, all four seeds and seeds 1-3.
    m_all = df.groupby("gamma_target").rho.mean()
    rep_only = df[df.gen_seed > 0]
    m_rep = rep_only.groupby("gamma_target").rho.mean()
    # 3. The dip on seeds 1-3 only: seed 0 is where the shape was first seen.
    s_rep = rep_only.groupby("gamma_target").rho.std(ddof=1)
    n = len(GEN_SEEDS)
    dip = float(m_rep[3.0] - 0.5 * (m_rep[2.1] + m_rep[4.0]))
    se = float(np.sqrt(s_rep[3.0] ** 2 / n + (s_rep[2.1] ** 2 + s_rep[4.0] ** 2) / (4 * n)))
    # 4. Structure drift per realisation.
    struct = df.groupby("gamma_target")[["lcc_n", "lcc_mean_degree", "nb_spectral_gap"]].agg(["mean", "std"])

    out = {"registered_in": "prereg 2026-11-02 23:30, part D (reported, none scored)",
           "s_gamma": {str(g): float(v) for g, v in s.items()},
           "sd_real": sd_real, "sd_fit": sd_fit, "sd_real_over_sd_fit": sd_real / sd_fit,
           "l6_sd_pool": json.loads((L6_OUT / "verdict.json").read_text(encoding="utf-8"))["primary"]["sd_pool"],
           "end_gap_all_seeds": float(m_all[2.1] - m_all[4.0]),
           "end_gap_seeds_1_3": float(m_rep[2.1] - m_rep[4.0]),
           "two_sd_real": 2 * sd_real,
           "dip_seeds_1_3": dip, "dip_se": se, "dip_over_se": dip / se,
           "structure": {f"{a}|{b}": {str(g): float(v) for g, v in struct[(a, b)].items()}
                         for a, b in struct.columns},
           "sources": {p: sha256(Path(p)) for p in ("probe_realisation.py", "probe_certificate.py")}}
    write_atomic(OUT / "calibration.json", json.dumps(out, indent=2) + "\n")
    pd.set_option("display.width", 200)
    print(df.round(4).to_string(index=False))
    print(json.dumps({k: v for k, v in out.items() if k not in ("structure", "sources")}, indent=2))
    print(struct.round(4).to_string())
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("prepare", "fit", "analyse"):
        raise SystemExit(__doc__)
    sys.exit({"prepare": run_prepare, "fit": run_fit, "analyse": run_analyse}[cmd]())
