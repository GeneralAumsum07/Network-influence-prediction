"""Regression gate for the graphlet-orbit radius tables.

Created 2026-09-11 by Claude Opus 5 for Task 6 root integration (finding P1-01;
also closes the gate gap recorded as P3-05).

Run with the project interpreter:
    C:/Users/Rachit/miniconda3/envs/influence/python.exe verify_calibration.py

WHY A GATE
----------
On 2026-09-11 the audit found that `_calib.calibrate` let the FIRST graph family
to touch an orbit fix its radius for ever, and voted "radius 1" for orbits a
family never contained at all. `influence/graphlets.py` said the table was the
MAXIMUM over families. It was not, and six 5-node node orbits (56, 57, 65, 66,
68, 70) plus nine 5-node edge orbits were tagged one hop too shallow. A shallow
tag lets a radius-r observer use a column it could not have computed, which can
only inflate that rung - and `verify_pipeline.py` guarded the 4-node table only.

TWO INDEPENDENT REFERENCES, NOT ONE
-----------------------------------
1. DERIVED. A radius-r observer sees the induced r-ball. An induced copy of a
   graphlet G containing v, with v in orbit k, lies inside v's r-ball iff every
   node of the copy is within r of v in the WHOLE graph, and whole-graph
   distance never exceeds within-graphlet distance. So r = ecc_G(v) always
   suffices, and a family in which the copy occurs with no shortcut needs
   exactly ecc_G(v). The 'never shallower' tag is therefore the eccentricity of
   the orbit's node inside its own graphlet, and it is computed here from the
   networkx graph atlas with no hand transcription.
2. MEASURED. `_calib.calibrate` applies the operational definition (ball count
   == whole-graph count for every node) on synthetic families. Any finite set of
   families can only UNDERSTATE the derived radius, never overstate it. So the
   measurement must be <= the derivation everywhere, and the two hand-derived
   4-node tables must be reproduced exactly by both.

The shipped tables must equal the DERIVED reference. Measurement is kept as the
check that the derivation matches the definition the project actually uses.
"""
from __future__ import annotations

import sys
import time

import numpy as np

from _calib import calibrate, derive_node_radius
from _calib_edge import calibrate_edge, derive_edge_radius
from influence import generators as gen
from influence.graphlets import (
    EDGE_ORBIT4_RADIUS,
    EDGE_ORBIT5_RADIUS,
    ORBIT5_RADIUS,
    ORBIT_SPEC,
)

FAIL: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))
    if not ok:
        FAIL.append(label)


def families() -> list[tuple[str, object]]:
    # The three families _calib.py has always used, in their historical order.
    return [("ER", gen.erdos_renyi(60, 6, seed=1)),
            ("BA", gen.barabasi_albert(60, 3, seed=2)),
            ("HK", gen.holme_kim(50, 3, 0.6, seed=3))]


def table_diff(shipped: dict[int, int], derived: dict[int, int]) -> list[tuple[int, int, int]]:
    return [(k, shipped[k], derived[k]) for k in sorted(derived) if shipped.get(k) != derived[k]]


def check_derived_tables() -> dict[str, dict[int, int]]:
    print("\n[1] shipped radius tables equal the eccentricity derivation")
    t0 = time.time()
    n4, n5 = derive_node_radius(4), derive_node_radius(5)
    e4, e5 = derive_edge_radius(4), derive_edge_radius(5)
    hand4 = {k: h for k, (_, h) in ORBIT_SPEC.items()}
    for label, shipped, derived, size in (
            ("4-node node orbits (hand table)", hand4, n4, 15),
            ("5-node node orbits", ORBIT5_RADIUS, n5, 73),
            ("4-node edge orbits (hand table)", EDGE_ORBIT4_RADIUS, e4, 12),
            ("5-node edge orbits", EDGE_ORBIT5_RADIUS, e5, 68)):
        check(f"{label}: every orbit derived", len(derived) == size,
              f"{len(derived)}/{size}")
        bad = table_diff(shipped, derived)
        check(f"{label}: shipped == derived", not bad,
              "" if not bad else "(orbit, shipped, derived) " + ", ".join(map(str, bad[:12])))
    print(f"      derivation took {time.time() - t0:.0f}s")
    return {"n4": n4, "n5": n5, "e4": e4, "e5": e5}


def check_measurement(derived: dict[str, dict[int, int]], full: bool) -> None:
    print("\n[2] measurement on synthetic families is order-invariant and never exceeds the derivation")
    fams = families()
    sizes = (4, 5) if full else (4,)
    for gs in sizes:
        t0 = time.time()
        fwd, seen_f = calibrate(fams, gs, max_r=4)
        rev, seen_r = calibrate(list(reversed(fams)), gs, max_r=4)
        check(f"node gs={gs}: calibrate order-invariant",
              np.array_equal(fwd, rev) and np.array_equal(seen_f, seen_r),
              f"{[k for k in range(len(fwd)) if fwd[k] != rev[k]]}" if not np.array_equal(fwd, rev) else "")
        ref = derived["n4"] if gs == 4 else derived["n5"]
        over = [(k, int(fwd[k]), ref[k]) for k in range(len(fwd)) if seen_f[k] and fwd[k] > ref[k]]
        check(f"node gs={gs}: measured <= derived on every seen orbit", not over, str(over[:8]))
        under = [(k, int(fwd[k]), ref[k]) for k in range(len(fwd)) if seen_f[k] and fwd[k] < ref[k]]
        # Understatement is allowed in principle (a family may realise only the
        # shortcut case) but must be printed, because it is exactly how the
        # 2026-09-11 defect hid: the families DID realise the worst case, and
        # the aggregation threw it away.
        print(f"      gs={gs}: measured strictly below derived on {len(under)} seen orbits {under[:8]}")
        if gs == 4:
            hand = {k: h for k, (_, h) in ORBIT_SPEC.items()}
            bad = [(k, int(fwd[k]), hand[k]) for k in range(15) if seen_f[k] and fwd[k] != hand[k]]
            check("node gs=4: measurement reproduces the hand table", not bad, str(bad))
        else:
            # The six orbits at the centre of P1-01 must now measure at 2 on the
            # families that first exposed them; if this ever prints 1 again the
            # aggregation has regressed.
            six = [56, 57, 65, 66, 68, 70]
            check("node gs=5: orbits 56,57,65,66,68,70 measure at radius 2",
                  all(int(fwd[k]) == 2 for k in six), str([int(fwd[k]) for k in six]))
        print(f"      gs={gs} node measurement took {time.time() - t0:.0f}s")

    t0 = time.time()
    fwd, seen_f = calibrate_edge(fams, 4, max_r=4)
    rev, seen_r = calibrate_edge(list(reversed(fams)), 4, max_r=4)
    check("edge gs=4: calibrate_edge order-invariant", np.array_equal(fwd, rev))
    over = [(k, int(fwd[k]), derived["e4"][k]) for k in range(12) if seen_f[k] and fwd[k] > derived["e4"][k]]
    check("edge gs=4: measured <= derived", not over, str(over))
    bad = [(k, int(fwd[k]), EDGE_ORBIT4_RADIUS[k]) for k in range(12) if seen_f[k] and fwd[k] != EDGE_ORBIT4_RADIUS[k]]
    check("edge gs=4: measurement reproduces the hand table", not bad, str(bad))
    print(f"      edge gs=4 measurement took {time.time() - t0:.0f}s")


def check_unseen_do_not_vote() -> None:
    """A family that never contains an orbit must not pin its radius.

    This is the second half of the 2026-09-11 defect: an all-zero column agrees
    with itself at radius 1, and the old code recorded that agreement as a
    radius-1 vote. A single triangle-free graph followed by a graph full of
    triangles must give the triangle orbit its true radius, whatever the order.
    """
    print("\n[3] a family without the orbit casts no vote")
    tree = gen.barabasi_albert(40, 1, seed=11)           # m=1: a tree, no triangles
    dense = gen.erdos_renyi(30, 12, seed=12)
    a, seen_a = calibrate([("tree", tree), ("dense", dense)], 4, max_r=3)
    b, seen_b = calibrate([("dense", dense), ("tree", tree)], 4, max_r=3)
    check("tree-first equals dense-first", np.array_equal(a, b) and np.array_equal(seen_a, seen_b),
          f"{a.tolist()} vs {b.tolist()}")
    check("triangle orbit (3) radius 1 either way", int(a[3]) == 1 and int(b[3]) == 1,
          f"{int(a[3])}, {int(b[3])}")
    check("orbit unseen in both families is reported unseen, radius 0",
          all(int(a[k]) == 0 for k in range(15) if not seen_a[k]))


def main(argv: list[str]) -> int:
    full = "--quick" not in argv
    derived = check_derived_tables()
    check_measurement(derived, full=full)
    check_unseen_do_not_vote()
    print()
    if FAIL:
        print(f"FAILURES ({len(FAIL)}):")
        for f in FAIL:
            print("  -", f)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
