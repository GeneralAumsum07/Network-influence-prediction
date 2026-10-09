"""Second recovery of the serial post-retag queue: stages 2 -> 3 -> 4 only.

Why a new controller instead of re-launching results/recovery_20260914/run.py:
  * That run (PID 23676) was killed on 2026-09-14 about 18:35, partway through the
    B1 sweep. No shutdown or power-loss event was logged; inferred cause: its
    launching session closed. Its active.lock is left in place as evidence.
  * It would refuse to resume anyway: L7's new influence/branch_anisotropy.py
    entered its influence/*.py glob, so the recorded source identity differs.
  * It has no stage skip, so it would re-enter stage 1 (buffered CV took 5.5 h).
    Stage 1 is complete (its controller.log: COMPLETE stage1_buffered, 17:28).
  * Its stage 2 would stop at Remove-PreRefit on the partial B1 CSV.
Nothing the old controller pinned is edited; this folder holds new copies.

Differences from the 2026-09-14 controller, each deliberate:
  1. Steps are stage2, stage3, stage4. Stage 1 completion is a precondition
     read from the 09-14 controller.log, not re-run.
  2. branch_anisotropy.py joins the deck-lane exclusions (L7 is zero-fit and
     still being written; it is not a dependency of this queue).
  3. The identity also pins the data inputs every stage reads (caches and
     sweep CSVs), not only code. The old resume trusted those by convention.
  4. --dry-run runs every precondition and prints the identity, then exits
     without taking the lock or launching anything.
  5. analyse.py is pinned. Six stage 2 scripts import it; the 09-14 identity
     omitted it.
Everything else (OS-level stdout/stderr files, exit codes, stop on failure,
source re-check before each stage, lock left behind on external kill) is kept.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PREVIOUS = ROOT / 'results/recovery_20260914'
NETS = ['ca-GrQc', 'ca-HepTh', 'email-Eu-core', 'facebook_combined', 'p2p-Gnutella08']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(message):
    print(f'{datetime.now().astimezone().isoformat()} {message}', flush=True)


def identity_sources():
    """Every file whose change would invalidate a resumed or queued result."""
    scripts = ['probe_sample_efficiency.py', 'analyse_sample_efficiency.py',
               'probe_objective_horizon.py', 'analyse_objective_horizon.py',
               'probe_target_noise.py', 'probe_target_noise_refit.py',
               'score_a7_arm2.py', 'analyse_paired_target_noise.py',
               'analyse_edge5.py', 'analyse_edge_tier.py',
               'analyse_robustness.py', 'make_fig3.py', 'verify_robustness_rerun.py',
               # Imported by six of the stage 2 scripts (both B1 scripts, both
               # objective-horizon scripts, both target-noise probes); checked
               # 2026-10-07. The 09-14 controller did not pin it, so an edit to
               # analyse.py would not have stopped that queue.
               'analyse.py']
    sources = [ROOT / name for name in scripts]
    # Phase 6.5 deck-lane modules: zero-fit, not imported by this queue, and must
    # stay editable while it runs. L7's module is new since 2026-09-14.
    deck_modules = {'nonbacktracking_local.py', 'seed_sets.py', 'local_dynamics.py',
                    'branch_anisotropy.py'}
    sources += [p for p in (ROOT / 'influence').glob('*.py') if p.name not in deck_modules]
    # Data inputs. The probes resume by key and do not check these themselves.
    for tag in NETS:
        sources += [ROOT / f'{kind}_{tag}.csv'
                    for kind in ('cache_features', 'cache_targets', 'cache_registry', 'sweep')]
    sources += [HERE / f'stage{s}.ps1' for s in (2, 3, 4)]
    # Stage 2 resume gates. The objective-horizon one was added 2026-10-07 when
    # that probe was made resumable; both decide whether a partial CSV is reused.
    sources += [HERE / 'check_b1_resume.py', HERE / 'check_objective_horizon_resume.py',
                Path(__file__)]
    return sources


def preconditions():
    """Refuse to start unless the state matches the 2026-10-07 inspection."""
    prev_log = (PREVIOUS / 'controller.log').read_text(encoding='utf-8')
    if 'COMPLETE stage1_buffered' not in prev_log:
        raise RuntimeError('stage 1 not recorded complete in recovery_20260914/controller.log')
    if 'COMPLETE stage2' in prev_log:
        raise RuntimeError('previous controller recorded stage 2 complete; this queue is stale')
    # The old lock names the killed PID. Starting while that PID is alive would
    # put two writers on the same CSVs.
    # Windows recycles PIDs, so "some process has this PID" is not enough: on
    # 2026-10-10 PID 23676 belonged to dllhost.exe (created 2026-10-07 19:45, after
    # a reboot), and the old bare check refused to start. The 09-14 controller was
    # python.exe, so only a python.exe holding that PID counts. A recycled PID that
    # lands on an unrelated python.exe still refuses - the safe direction.
    old_lock = PREVIOUS / 'active.lock'
    if old_lock.exists():
        pid = old_lock.read_text().strip()
        alive = subprocess.run(['tasklist', '/FI', f'PID eq {pid}',
                                '/FI', 'IMAGENAME eq python.exe', '/NH'],
                               capture_output=True, text=True).stdout
        if pid in alive:
            raise RuntimeError(f'previous controller PID {pid} is still alive as python.exe')
    missing = [p for p in identity_sources() if not p.exists()]
    if missing:
        raise RuntimeError(f'missing inputs: {[p.relative_to(ROOT).as_posix() for p in missing]}')


def main():
    dry = '--dry-run' in sys.argv[1:]
    preconditions()
    identity = {p.relative_to(ROOT).as_posix(): digest(p) for p in identity_sources()}
    manifest = HERE / 'sources.json'
    if dry:
        if manifest.exists():
            same = json.loads(manifest.read_text()) == identity
            print(f'recorded manifest present; identity {"MATCHES" if same else "DIFFERS"}')
        print(f'dry run: preconditions PASS; {len(identity)} files pinned; nothing launched')
        return 0

    # Exclusive process-lifetime lock prevents two writers. A crash leaves the
    # lock as evidence requiring inspection instead of silently starting twice.
    lock = HERE / 'active.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    success = False
    try:
        if manifest.exists():
            if json.loads(manifest.read_text()) != identity:
                raise RuntimeError('Recovery source identity changed; refusing resume')
        else:
            manifest.write_text(json.dumps(identity, indent=2) + '\n')
        steps = [('stage2', HERE / 'stage2.ps1'),
                 ('stage3', HERE / 'stage3.ps1'),
                 ('stage4', HERE / 'stage4.ps1')]
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        for name, script in steps:
            if any(digest(ROOT / path) != value for path, value in identity.items()):
                raise RuntimeError('Source or input changed while queued; stopping before next step')
            log(f'BEGIN {name}')
            with (HERE / f'{name}.out.log').open('ab') as stdout, \
                    (HERE / f'{name}.err.log').open('ab') as stderr:
                result = subprocess.run(
                    ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                     '-File', str(script)], cwd=ROOT, env=env,
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            if result.returncode:
                raise RuntimeError(f'{name} exited {result.returncode}; inspect its logs')
            log(f'COMPLETE {name}')
        success = True
        log('RECOVERY ALL STAGES COMPLETE')
    except Exception as exc:
        log(f'FAILED {exc}')
        raise
    finally:
        # Normal failures have no live child and can be retried after inspection.
        # An externally killed process never reaches this line, so its lock stays.
        lock.unlink()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
