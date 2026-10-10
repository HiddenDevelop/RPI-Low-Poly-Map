"""Append-only public GIS acquisition. Run from any directory; never overwrites.

Commands: discover, osm-pilot, elevation-search, download URL RELATIVE_PATH,
verify. Requests and responses are retained verbatim with HTTP provenance.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'gis/raw'
ENDPOINT = 'https://overpass-api.de/api/interpreter'
SESSION = requests.Session()
SESSION.headers['User-Agent'] = 'RPI-campus-GIS-research/1.0 (public data acquisition)'

def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data if isinstance(data, bytes) else data.encode('utf-8'))

def fetch(url, relative, params=None, query=None):
    if (RAW/'SHA256SUMS.txt').exists():
        raise RuntimeError('Raw acquisition sealed; use a new snapshot directory for further downloads.')
    dest = RAW / relative
    if not dest.resolve().is_relative_to(RAW.resolve()):
        raise ValueError('Destination outside raw directory')
    if dest.exists() or dest.with_suffix(dest.suffix + '.http.json').exists():
        raise FileExistsError(dest)
    started = datetime.now(timezone.utc).isoformat()
    r = SESSION.post(url, data={'data': query}, timeout=(30, 240)) if query else SESSION.get(url, params=params, timeout=(30, 240))
    r.raise_for_status()
    if 'json' in r.headers.get('Content-Type', ''):
        value = r.json()
        if value.get('remark') or value.get('error'):
            raise RuntimeError(value)
    write_new(dest, r.content)
    meta = {'requested_url': url, 'resolved_url': r.url, 'method': r.request.method,
            'parameters': params, 'query': query, 'download_started_utc': started,
            'download_completed_utc': datetime.now(timezone.utc).isoformat(),
            'response_headers': dict(r.headers), 'bytes': len(r.content),
            'sha256': hashlib.sha256(r.content).hexdigest()}
    write_new(dest.with_suffix(dest.suffix + '.http.json'), json.dumps(meta, indent=2))
    print(json.dumps({'file': str(dest), 'bytes': len(r.content), 'sha256': meta['sha256']}), flush=True)
    return r.content

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['discover','osm-pilot','elevation-search','nys-pilot','download','verify'])
    parser.add_argument('args', nargs='*')
    a = parser.parse_args()
    if a.action == 'discover':
        q = '[out:json][timeout:120];nwr["building"](around:1200,42.729014,-73.676728);out meta geom;\n'
        write_new(RAW/'osm/discovery.overpassql', q)
        fetch(ENDPOINT, 'osm/discovery.json', query=q)
    elif a.action == 'osm-pilot':
        area = json.loads((ROOT/'gis/pilot_area.json').read_text())
        w,s,e,n = area['bbox_wgs84']
        stamp = area['osm_snapshot_utc']
        q = f'[out:json][timeout:180][date:"{stamp}"];(nwr({s},{w},{n},{e}););(._;>>;);out meta;\n'
        write_new(RAW/'osm/pilot.overpassql', q)
        fetch(ENDPOINT, 'osm/pilot.json', query=q)
    elif a.action == 'elevation-search':
        box = json.loads((ROOT/'gis/pilot_area.json').read_text())['bbox_wgs84']
        for label,dataset in [('1m','Digital Elevation Model (DEM) 1 meter'),('opr','Digital Elevation Model (DEM) - Original Product Resolution')]:
            fetch('https://tnmaccess.nationalmap.gov/api/v1/products', f'elevation/products_{label}.json',
                  params={'bbox': ','.join(map(str,box)), 'datasets':dataset,'max':100,'outputFormat':'JSON'})
    elif a.action == 'nys-pilot':
        box = json.loads((ROOT/'gis/pilot_area.json').read_text())['bbox_wgs84']
        fetch('https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer/2/query',
              'nys/pilot_buildings.json', params={'f':'json','where':'1=1','geometry':','.join(map(str,box)),
              'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects',
              'outFields':'*','returnGeometry':'true','returnZ':'true','orderByFields':'OBJECTID','resultRecordCount':50000})
    elif a.action == 'download':
        if len(a.args) != 2:
            parser.error('download requires URL and relative destination')
        fetch(a.args[0], a.args[1])
    else:
        recorded = set()
        for line in (RAW/'SHA256SUMS.txt').read_text().splitlines():
            expected, relative = line.split('  ', 1)
            if not (RAW/relative).resolve().is_relative_to(RAW.resolve()):
                raise RuntimeError('Hash manifest path escapes raw directory')
            recorded.add(relative)
            actual = hashlib.sha256((RAW/relative).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(f'Hash mismatch: {relative}')
        present = {p.relative_to(RAW).as_posix() for p in RAW.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt'}
        if recorded != present:
            raise RuntimeError(f'Unrecorded or missing files: {recorded ^ present}')
        print('All recorded raw SHA-256 hashes match.')

if __name__ == '__main__':
    main()
