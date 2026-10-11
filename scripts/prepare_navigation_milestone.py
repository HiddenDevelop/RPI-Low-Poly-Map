"""Source-preserving JEC/DCC/Greene navigation evidence and presentation inputs.

No source edits, snapping, level-to-height conversion, or route certification.
Run once per unique output folder; --out supports deterministic comparison runs.
"""
import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from pyproj import datadir, network
from pyproj.transformer import TransformerGroup
from shapely.geometry import shape, box, Point, Polygon, mapping
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
RUN = 'rpi_navigation_20261011_pass04'
OUT = ROOT / 'gis/cleaned' / RUN

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def write(p, value):
    with p.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=False)
    roi = box(607922,4731519,608169,4731709)
    original = read(ROOT / 'blender/working/rpi_lowpoly_20261010_01_payload.json')
    by_id = {d['feature']['id']:d for d in original['features']}
    features = {}
    for layer in ['paths','stairs','entrances','accessibility']:
        for f in read(ROOT / ('gis/cleaned/pilot/osm/' + layer + '.json'))['features']:
            if shape(f['geometry']).intersects(roi):
                features[f['id']] = f
    records = []
    edges = []
    incidence = defaultdict(list)
    for key, f in sorted(features.items()):
        tags = f['source'].get('tags', {})
        elevated = tags.get('layer') == '1' or tags.get('level') == '1' or tags.get('bridge') == 'yes'
        underground = tags.get('tunnel') not in (None,'no') or tags.get('layer') == '-1' or '-' in tags.get('level','')
        context = 'elevated' if elevated else 'underground_or_transition' if underground else 'surface_or_unknown'
        width = float(tags['width']) if tags.get('width','').replace('.','',1).isdigit() else None
        record = {'id': key, 'feature': f, 'context': context, 'surface': tags.get('surface'),
                  'width_m': width, 'width_status': 'source tag, unverified' if width is not None else 'unknown',
                  'wheelchair': tags.get('wheelchair'), 'level': tags.get('level'), 'layer': tags.get('layer'),
                  'routing_eligibility': 'not_validated', 'source_nodes': f['source'].get('nodes',[]),
                  'display': by_id.get(key), 'display_width_m': width if width is not None else 1.6}
        records.append(record)
        if f['geometry']['type'] != 'LineString':
            continue
        nodes = f['source']['nodes']
        coords = f['geometry']['coordinates']
        assert len(nodes) == len(coords)
        for i, node in enumerate(nodes):
            incidence[str(node)].append({'source_id': key, 'index': i, 'level':tags.get('level'), 'layer':tags.get('layer')})
        for i, (a,b) in enumerate(zip(nodes,nodes[1:])):
            edges.append({'id': key + '/segment/' + str(i), 'source_id': key, 'index': i,
                          'from_node': a, 'to_node': b, 'xy': coords[i:i+2],
                          'length_xy_m': math.dist(coords[i],coords[i+1]),
                          'level':tags.get('level'), 'layer':tags.get('layer'), 'wheelchair':tags.get('wheelchair')})
    entrances = [{'id':r['id'], 'node_id':r['feature']['source']['id'],
                  'way_incidence':incidence.get(str(r['feature']['source']['id']),[]),
                  'level':r['level'], 'accessibility':r['wheelchair']} for r in records
                 if 'entrance' in r['feature']['source'].get('tags',{})]
    mixed = {n:rows for n,rows in incidence.items() if len({(r['level'],r['layer']) for r in rows}) > 1}
    # Record geometric crossings but NEVER manufacture a graph junction there.
    crossings = []
    lines = [r for r in records if r['feature']['geometry']['type']=='LineString']
    for i,a in enumerate(lines):
        for b in lines[i+1:]:
            if set(a['source_nodes']) & set(b['source_nodes']):
                continue
            cross = shape(a['feature']['geometry']).intersection(shape(b['feature']['geometry']))
            if not cross.is_empty:
                crossings.append({'source_ids':[a['id'],b['id']], 'geometry':mapping(cross),
                                  'action':'No connection added; review grade separation and source topology.'})
    network.set_network_enabled(False)
    datadir.append_data_dir(str(ROOT/'gis/acquisitions/evidence_20261010_01/source/datum'))
    group = TransformerGroup(6537,26918,always_xy=True,allow_ballpark=False)
    assert group.best_available and group.transformers
    t = group.transformers[0]
    # Two visually identifiable canopy centers in the reviewed JEC courtyard image.
    # These are evidence annotations, NOT surveyed trunk locations or obstacles.
    trees = []
    for i,(x,y,r) in enumerate([(712462,1420468,2.3),(712486,1420424,3.4)]):
        xx,yy = t.transform(x,y)
        trees.append({'id': f'imagery/canopy/{i+1:02d}', 'geometry':mapping(Point(xx,yy)),
            'native_center_ftUS':[x,y], 'display_radius_m':r, 'display_height_m':6.0,
            'position_status':'Approximate canopy center manually interpreted from 2024 aerial imagery; trunk unknown',
            'size_status':'Illustrative; not measured', 'routing_obstacle':None,
            'reference':'gis/cleaned/evidence_20261010_01/osm_way_104737275_review.png'})
    plaza_native = Polygon([(712445,1420493),(712535,1420480),(712530,1420404),
                            (712504,1420380),(712458,1420384),(712438,1420422)])
    plaza = transform(t.transform,plaza_native)
    buildings = read(ROOT/'gis/cleaned/pilot/osm/buildings.json')['features']
    for b in buildings:
        plaza = plaza.difference(shape(b['geometry']))
    landscape = {'crs':'EPSG:26918','units':'metres','origin_offset':[0,0,0],
        'datum_operation':{'pipeline':t.definition,'accuracy_m':t.accuracy},
        'trees':trees,'plaza_review':{'id':'imagery/plaza/jec_courtyard','geometry':mapping(plaza),
        'status':'Approximate visual pavement envelope; not measured edges or a routable surface',
        'surface':None,'reference':'gis/cleaned/evidence_20261010_01/osm_way_104737275_review.png'},
        'imagery_sha256':hashlib.sha256((ROOT/'gis/cleaned/evidence_20261010_01/osm_way_104737275_review.png').read_bytes()).hexdigest()}
    notice = {'id':'rpi/jec-dcc/2026-09-14','source_url':'https://administration.rpi.edu/announcements/dcc-jec-upper-deck-walkway-closure',
        'review_date':'2026-10-11','start_date':'2026-09-14',
        'status':'Closure notice published; present reopening status unconfirmed',
        'expected_duration':'approximately three weeks, not a confirmed end date',
        'scope':'JEC–DCC upper deck; exact OSM segment mapping unverified',
        'routing_effect':'Do not offer this as a verified available route; confirm posted detour and current campus status.',
        'source_geometry_updated':False}
    report = {'passed':True,'source_features':len(records),'source_segments':len(edges),
        'source_nodes':len(incidence),'bridge_spans':sum(r['feature']['source'].get('tags',{}).get('bridge')=='yes' for r in records),
        'elevated_features':sum(r['context']=='elevated' for r in records),
        'surfaces':dict(Counter(r['surface'] or 'unknown' for r in lines)),
        'widths_known_from_tags':sum(r['width_m'] is not None for r in lines),
        'entrances':len(entrances),'entrances_without_shared_way_node':sum(not e['way_incidence'] for e in entrances),
        'mixed_level_node_reviews':len(mixed),'crossings_without_shared_node':len(crossings),
        'boundary_crossing_features_retained':sum(not roi.covers(shape(r['feature']['geometry'])) for r in records),
        'source_xy_changes':0,'new_graph_junctions':0,'inferred_accessibility_values':0,
        'navigation_ready':False,'landscape_annotations':len(trees)}
    write(out/'features.json',{'schema':'rpi-navigation-evidence-v1','crs':'EPSG:26918','units':'metres',
          'origin_projected_m':original['origin_projected_m'],'aoi':mapping(roi),'records':records})
    write(out/'source_topology.json',{'segments':edges,'node_incidence':dict(sorted(incidence.items())),
          'entrance_review':entrances,'mixed_level_nodes':mixed,'geometric_crossing_review':crossings,
          'policy':'Source topology inventory, not a routable graph; level and layer are distinct; no spatial snapping.'})
    write(out/'landscape_review.json',landscape)
    write(out/'closure_review.json',notice)
    write(out/'validation.json',report)
    write(out/'manifest.json',{'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.json'))},
        'source_manifest_sha256':hashlib.sha256((ROOT/'gis/cleaned/pilot/manifest.json').read_bytes()).hexdigest()})
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
