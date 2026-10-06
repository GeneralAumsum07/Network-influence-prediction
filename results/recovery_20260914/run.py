"""Recover the interrupted serial queue without changing scientific modules.

Use OS file handles for child stdout/stderr. In particular, a native warning
must not become a PowerShell terminating ErrorRecord in an outer pipeline.
The repaired stage copies also avoid PowerShell's automatic $Args variable.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(message):
    print(f'{datetime.now().astimezone().isoformat()} {message}', flush=True)


def main():
    # Exclusive process-lifetime lock prevents two recovery writers. A crash
    # leaves evidence requiring inspection instead of silently starting twice.
    lock = HERE / 'active.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    success = False
    try:
        scripts = ['probe_structural_target_noise_refit.py',
                   'analyse_structural_target_noise.py', 'probe_buffered_cv.py',
                   'analyse_buffered_cv.py', 'analyse_structural_moran_correlogram.py',
                   'probe_sample_efficiency.py', 'analyse_sample_efficiency.py',
                   'probe_objective_horizon.py', 'analyse_objective_horizon.py',
                   'probe_target_noise.py', 'probe_target_noise_refit.py',
                   'score_a7_arm2.py', 'analyse_paired_target_noise.py',
                   'analyse_edge5.py', 'analyse_edge_tier.py',
                   'analyse_robustness.py', 'make_fig3.py', 'verify_robustness_rerun.py',
                   'results/phase6_structural_controller.ps1',
                   'results/phase6_buffered_controller.ps1']
        sources = [ROOT / name for name in scripts]
        # The independent, unfinished deck-lane modules are not dependencies of
        # this queue and must remain editable while the production runs wait.
        deck_modules = {'nonbacktracking_local.py', 'seed_sets.py', 'local_dynamics.py'}
        sources += [p for p in (ROOT / 'influence').glob('*.py')
                    if p.name not in deck_modules]
        sources += [HERE / f'stage{s}.ps1' for s in (2, 3, 4)] + [Path(__file__)]
        identity = {p.relative_to(ROOT).as_posix(): digest(p) for p in sources}
        manifest = HERE / 'sources.json'
        if manifest.exists():
            if json.loads(manifest.read_text()) != identity:
                raise RuntimeError('Recovery source identity changed; refusing resume')
        else:
            manifest.write_text(json.dumps(identity, indent=2) + '\n')
        steps = [
            ('stage1_structural', ROOT / 'results/phase6_structural_controller.ps1'),
            ('stage1_buffered', ROOT / 'results/phase6_buffered_controller.ps1'),
            ('stage2', HERE / 'stage2.ps1'),
            ('stage3', HERE / 'stage3.ps1'),
            ('stage4', HERE / 'stage4.ps1'),
        ]
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        for name, script in steps:
            if any(digest(ROOT / path) != value for path, value in identity.items()):
                raise RuntimeError('Source changed while queued; stopping before next step')
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
        # Normal failures have no live child and can safely be retried after
        # inspection. An externally killed process leaves its lock in place.
        lock.unlink()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
