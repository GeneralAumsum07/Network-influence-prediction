"""Import-path setup shared by the scripts in this folder.

The scripts sit one level below the repository root. They import the
``influence`` package from the root and each other by bare module name
(``from analyse import FULL``, ``from probe_beta_sweep import run_stage``).
Importing this module first puts the root and every script folder on
``sys.path`` so those imports resolve. Data paths stay root-relative: run the
scripts from the repository root, e.g. ``python analysis/analyse.py``.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("pipeline", "analysis", "probes", "checks", "figures")

for _p in (ROOT, *(ROOT / f for f in FOLDERS)):
    if str(_p) not in sys.path:
        sys.path.insert(1, str(_p))
