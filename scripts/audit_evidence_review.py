"""Seal the separate acquisition and verify protected inputs and repeatability."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'gis/acquisitions/evidence_20261010_01'
REVIEW = ROOT / 'gis/cleaned/evidence_20261010_01'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source = SNAPSHOT / 'source'
    inventory = {p.relative_to(source).as_posix(): sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    seal = SNAPSHOT / 'SHA256SUMS.txt'
    content = ''.join(f'{digest}  {name}\n' for name, digest in inventory.items())
    if seal.exists():
        assert seal.read_text(encoding='utf-8') == content, 'Acquisition seal mismatch'
    else:
        with seal.open('x', encoding='utf-8', newline='\n') as f:
            f.write(content)
    # Separate process deliberately does not inherit the evidence-only datum grid path.
    validation = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_pilot_gis.py')],
                                cwd=ROOT, capture_output=True, text=True, check=True)
    pilot = json.loads(validation.stdout)
    protected = ['gis/raw', 'gis/cleaned/pilot', 'blender', 'scripts/import_gis.py', 'scripts/validate_scene.py']
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', *protected], cwd=ROOT, check=True)
    # Compare full .blend file bytes to the committed LFS SHA-256, not scene placeholders.
    tracked = subprocess.check_output(['git', 'ls-files', 'blender'], cwd=ROOT, text=True).splitlines()
    blends = {}
    for name in tracked:
        if not name.endswith('.blend'):
            continue
        pointer = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT, text=True)
        expected = next(line.split('sha256:')[1] for line in pointer.splitlines() if line.startswith('oid sha256:'))
        assert sha(ROOT / name) == expected, name
        blends[name] = expected
    rerun = Path(tempfile.mkdtemp(prefix='evidence_repeatability_', dir=ROOT / '.local'))
    subprocess.run([sys.executable, str(ROOT / 'scripts/finish_evidence_review.py'), '--out', str(rerun)], cwd=ROOT, check=True)
    repeated = ['elevation_review.json', 'discrepancy_review.json', 'review_validation.json']
    for name in repeated:
        assert sha(REVIEW / name) == sha(rerun / name), name
    result = {'passed': True, 'sealed_source_files': len(inventory), 'pilot_validation': pilot,
              'protected_git_paths_unchanged': protected, 'blend_sha256_matches_committed_baseline': blends,
              'deterministic_rebuild_matches': repeated,
              'scope': 'No scene edited. Byte identity preserves scene geometry/topology/metadata; no new semantic Blender validation claimed.'}
    report = REVIEW / 'integrity_validation.json'
    if report.exists():
        assert json.loads(report.read_text(encoding='utf-8')) == result
    else:
        with report.open('x', encoding='utf-8', newline='\n') as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write('\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
