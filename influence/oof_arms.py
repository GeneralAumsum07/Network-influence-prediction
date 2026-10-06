"""
Which stored out-of-fold prediction archive a reader should open.

Created 2026-09-11 by Claude Opus 5 for Task 6 root integration (finding P2-03).

THE PROBLEM THIS SOLVES
-----------------------
Betweenness has two prediction archives on disk:

  cache_oof_<tag>.npz                          random forest, squared-error
                                               objective ("raw" arm) - the
                                               historical Finding 8 fits
  estimators/cache_oof_<tag>__rf_log1p.npz     random forest, log1p objective
                                               - the arm the study REPORTS
                                               since the 2026-09-04 re-basing

Every other target has one archive only (the top-level file). Before this
module, `analyse_betweenness.load_oof` and `analyse_failures.compute` opened
the top-level file for betweenness while `analyse_moran_correlogram.oof_store`
opened the rf_log1p file, so two artifacts described two different models
under one name, and the taus are close enough that nothing downstream noticed.

Readers now ask this module for the archive, say which arm they got, and print
it in their headers. The default is the reported arm; `arm="raw"` is the
explicit way to reproduce a historical raw-arm artifact, and the caller must
label it as such.
"""
from __future__ import annotations

import os

import numpy as np

# Objective arm the study reports for each target. Targets not listed have a
# single arm, "raw", which is also the only archive that exists for them.
REPORTED_ARM: dict[str, str] = {"betweenness": "log1p"}

ARMS = ("raw", "log1p")


def reported_arm(target: str) -> str:
    return REPORTED_ARM.get(target, "raw")


def oof_path(tag: str, target: str, arm: str | None = None) -> tuple[str, str]:
    """
    (path, arm) of the archive holding `target`'s predictions under `arm`.

    `arm=None` means the reported arm. Asking for "log1p" on a target that was
    never swept under log1p is an error, not a silent fallback - the whole
    point is that the caller knows exactly what it is reading.
    """
    arm = reported_arm(target) if arm is None else arm
    if arm not in ARMS:
        raise ValueError(f"unknown objective arm {arm!r}; expected one of {ARMS}")
    if arm == "raw":
        return f"cache_oof_{tag}.npz", arm
    if target != "betweenness":
        raise ValueError(f"the log1p arm exists for betweenness only, not {target!r}")
    return os.path.join("estimators", f"cache_oof_{tag}__rf_log1p.npz"), arm


def load_oof(tag: str, target: str, arm: str | None = None) -> tuple[dict | None, str]:
    """
    (store, arm): the prediction vectors for `target` keyed
    `target|radius|richness|seed`, or None when the archive is absent.

    Only `target`'s keys are returned, so a reader cannot accidentally mix the
    log1p file's betweenness with another target's raw predictions.
    """
    path, arm = oof_path(tag, target, arm)
    if not os.path.exists(path):
        return None, arm
    with np.load(path) as z:
        return {k: z[k] for k in z.files if k.startswith(f"{target}|")}, arm


def arm_label(target: str, arm: str) -> str:
    """One-line provenance string for report headers and figure titles."""
    if arm == "log1p":
        return f"objective: log1p {target} (reported arm)"
    if target in REPORTED_ARM:
        return f"objective: raw {target} (historical arm; the study reports {REPORTED_ARM[target]})"
    return f"objective: raw {target}"
