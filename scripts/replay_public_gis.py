"""Replay saved requests into a NEW raw snapshot directory (never overwrite).

Usage: python scripts/replay_public_gis.py SNAPSHOT_NAME
Live catalogs may change: frozen bytes + SHA256SUMS are the exact reproducible
baseline. OSM pilot request pins its historical date; discovery is pinned here
to the archived discovery response's base timestamp.
"""
import argparse
import json
import re
import acquire_public_gis as acquisition

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('name')
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',a.name):
        p.error('Use a simple snapshot name, at most 64 characters.')
    original=acquisition.RAW
    dest=acquisition.ROOT/'gis/acquisitions'/a.name/'raw'
    if dest.exists(): raise FileExistsError(dest)
    records=json.loads((original/'sources.json').read_text())['downloads']
    stamp=json.loads((original/'osm/discovery.json').read_text())['osm3s']['timestamp_osm_base']
    acquisition.RAW=dest
    for record in records:
        q=record.get('query')
        if record['file']=='osm/discovery.json':
            q=q.replace('[out:json]',f'[out:json][date:"{stamp}"]',1)
        acquisition.fetch(record['requested_url'],record['file'],record.get('parameters'),q)
    print('New responses saved. Review and seal separately; do not replace the original baseline.')

if __name__=='__main__': main()
