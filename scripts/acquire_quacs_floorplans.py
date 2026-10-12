"""Acquire pinned reference plans; never writes raw GIS or existing outputs."""
import hashlib, json, urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'gis/acquisitions/quacs_floorplans_20261011_01'
COMMIT = '08c82580638b3e9a3816802f3e1ba98a30383f13'
FILES = [{"name":"darrin-1.pdf","sha":"a8b55a9bb88cfa5a9c1d3bee4a80afbce1431635"},{"name":"darrin-2.pdf","sha":"67f9b75591ce809335e1f4302287453e7cad8962"},{"name":"darrin-3.pdf","sha":"e393577cb045d8dc88f7e45eda61d2ee9cb5a309"},{"name":"greene-1.pdf","sha":"8179b290287ba5b72029869558c667ec8bcf5ee1"},{"name":"greene-2.pdf","sha":"9c8f4c78dfca02f7789455a60bffe5358b9e0dc3"},{"name":"greene-3.pdf","sha":"f850cdff9d394fa0f677318367a651cfc3ede87a"},{"name":"greene-4.pdf","sha":"fa070fdc2c79e9203a4efa8d65c19510f7523fd6"},{"name":"greene-b.pdf","sha":"1ecb59f781e777a21d55e040034779bbef9bdbf5"},{"name":"greene_mz.pdf","sha":"1a10de9d8cbe479972760f7cdd298d3c6466fb38"},{"name":"jonssonengctr1000.pdf","sha":"4209bf7ad9d8574e4a8cfeeed1903e1d8812bbe4"},{"name":"jonssonengctr2000.pdf","sha":"6e868afb0fa2b51a81390fb438da8042bc90a842"},{"name":"jonssonengctr3000.pdf","sha":"b4f7a34a1bbbd1f182ed5a295648d9ddda504f30"},{"name":"jonssonengctr4000.pdf","sha":"97818e1c0f0c5b3c5bdbcddec875f20f0861fe89"},{"name":"jonssonengctr5000.pdf","sha":"3b156ea6290644afee3584dddf67a16e4670260f"},{"name":"jonssonengctr6000.pdf","sha":"282987ff3d823e8b1ed0baa773273680e1cbee42"},{"name":"jonssonengctr7000.pdf","sha":"0533c59fa2ab3375ed3e5178dee2529f8bceb871"},{"name":"jonssonengctr_roof.pdf","sha":"71bc900163df192bf6d25901931fc520cece4038"}]

def main():
    OUT.mkdir(parents=True, exist_ok=False)
    entries = []
    for item in sorted(FILES + [{'name': 'LICENSE', 'sha': None}, {'name': 'README.md', 'sha': None}], key=lambda x:x['name']):
        rel = item['name'] if item['name'] in ('LICENSE', 'README.md') else 'floor_plans/' + item['name']
        url = f'https://raw.githubusercontent.com/quacs/quacs-data/{COMMIT}/{rel}'
        data = urllib.request.urlopen(url, timeout=60).read()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if item['sha'] and blob != item['sha']:
            raise ValueError('Git blob mismatch: ' + rel)
        (OUT / item['name']).write_bytes(data)
        entries.append(dict(path=item['name'], source_url=url, git_blob_sha1=blob, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
    manifest = dict(commit=COMMIT, acquired_utc=datetime.now(timezone.utc).isoformat(), repository_license='MIT; retained LICENSE. Original drawing rights/provenance require separate review.', crs=None, ground_units=None, local_origin=None, datum_operation='None. PDF page coordinates are not geographic coordinates.', accessibility='Unknown; drawings are not current accessibility certification.', files=entries)
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    paths=sorted(p for p in OUT.iterdir() if p.is_file())
    (OUT/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths), encoding='utf-8')
    print(f'Acquired and Git-blob verified {len(FILES)} plans.')

if __name__ == '__main__':
    main()

