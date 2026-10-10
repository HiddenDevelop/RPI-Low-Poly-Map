"""Shared, explicit schema and lossless geometry parsing for the RPI pilot.

These are source geometry layers, never a routing graph. Coordinates are in
EPSG:26918 meters, with no local offset and no vertical transformation.
"""
import hashlib
import json
import math
from pathlib import Path

import pyproj
from pyproj import Transformer, network
from pyproj.transformer import AreaOfInterest, TransformerGroup
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon, box, mapping
from shapely.validation import explain_validity

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'gis/raw'
SCHEMA = 'rpi-source-layer-v1'
CRS = 'EPSG:26918'
PIPELINE = 'proj=pipeline step proj=unitconvert xy_in=deg xy_out=rad step proj=utm zone=18 ellps=GRS80'
LAYERS = ('buildings','paths','roads','stairs','landcover','entrances','accessibility','other')
ROADS = {'motorway','trunk','primary','secondary','tertiary','unclassified','residential','service','living_street','road','motorway_link','trunk_link','primary_link','secondary_link','tertiary_link'}
PATHS = {'path','footway','pedestrian','cycleway','bridleway'}
SEMANTICS = ('level','level:ref','layer','indoor','bridge','tunnel','covered','location',
             'repeat_on','min_level','max_level','highway','entrance','wheelchair','access',
             'foot','ramp','ramp:wheelchair','incline','conveying','step_count','kerb',
             'tactile_paving','surface','smoothness','width','handrail')

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def verify_raw():
    recorded = {}
    for line in (RAW/'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ',1)
        path = RAW/name
        if name in recorded or not path.resolve().is_relative_to(RAW.resolve()):
            raise ValueError('Invalid/duplicate raw manifest path')
        if sha(path) != digest:
            raise ValueError(f'Raw integrity failure: {name}')
        recorded[name] = digest
    actual = {p.relative_to(RAW).as_posix() for p in RAW.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    if actual != set(recorded):
        raise ValueError(f'Raw file inventory changed: {actual ^ set(recorded)}')
    return recorded

def sid(element):
    return f"osm/{element['type']}/{element['id']}"

def classifications(e):
    t=e.get('tags',{}); layers=[]
    if t.get('building') not in (None,'no'): layers.append('buildings')
    if t.get('highway') in PATHS: layers.append('paths')
    if t.get('highway') in ROADS: layers.append('roads')
    if t.get('highway')=='steps': layers.append('stairs')
    if 'landuse' in t or 'landcover' in t or t.get('natural') in {'wood','scrub','grassland','water','wetland','tree','tree_row'}: layers.append('landcover')
    if 'entrance' in t: layers.append('entrances')
    if any(k.startswith(('wheelchair','ramp','kerb','tactile_paving')) for k in t) or t.get('highway')=='elevator' or t.get('barrier')=='kerb': layers.append('accessibility')
    return layers or ['other']

def transformer():
    network.set_network_enabled(False)
    return Transformer.from_pipeline(PIPELINE)

def operation_record(bounds):
    network.set_network_enabled(False)
    group=TransformerGroup(4326,26918,always_xy=True,area_of_interest=AreaOfInterest(*bounds),allow_ballpark=False)
    found=[t for t in group.transformers if t.definition==PIPELINE and t.accuracy==4.0]
    if len(found)!=1: raise ValueError('Pinned operation is not available as expected; review CRS environment')
    t=found[0]
    return {'input_crs':'EPSG:4326','output_crs':CRS,'input_axis_order':'longitude,latitude',
            'output_axis_order':'easting,northing','units':'metre','local_origin_offset':[0,0],
            'name':t.description,'operation_id':'Inverse EPSG:1188 then EPSG:16018',
            'pipeline':PIPELINE,'stated_operation_accuracy_m':4.0,'ballpark_allowed':False,
            'network_enabled':False,'grids_used':[],'best_available':group.best_available,
            'unavailable_operations':[{'name':op.name,'accuracy_m':op.accuracy,
                 'grids':[{'name':g.short_name,'available':g.available,'url':g.url} for g in op.grids]} for op in group.unavailable_operations],
            'selection_reason':'Pin installed non-ballpark operation used in acquisition inspection. No grid downloads or silent environment-dependent substitution. This is not survey accuracy.',
            'pyproj_version':pyproj.__version__,'proj_version':pyproj.proj_version_str,
            'proj_database_sha256':sha(Path(pyproj.datadir.get_data_dir())/'proj.db'),
            'projjson':t.to_json_dict(),'nys_operation':'Identity EPSG:26918 -> EPSG:26918; native XY and ring vertices preserved',
            'vertical_operation':'None. OSM level/ele strings are not geometric Z; NYS raw Z retained only in source record with unknown vertical semantics. DEM NAVD88 referenced, not resampled or sampled onto vectors.',
            'limitations':'No sub-meter geographic alignment guarantee. Unknown OSM datum realization/epoch and source error remain unknown. No accessibility inference.'}

def checked(g, label):
    if g.is_empty or not g.is_valid:
        raise ValueError(f'{label}: empty/invalid geometry: {explain_validity(g)}')
    if not all(math.isfinite(v) for v in g.bounds): raise ValueError(f'{label}: nonfinite coordinates')
    if g.geom_type in ('Polygon','MultiPolygon') and g.area<=1e-9: raise ValueError(f'{label}: zero area')
    if g.geom_type=='LineString' and g.length<=1e-9: raise ValueError(f'{label}: zero length; do not infer vertical connection')
    return g

def assemble_rings(members, index):
    """Join only identical source endpoint IDs, never coincident coordinates.

    Every member occurrence is retained in ring provenance; branches, missing
    references, unsupported member types/roles and unclosed chains fail.
    """
    remaining=[]
    for position,m in members:
        if m['type']!='way': raise ValueError('Multipolygon member must be a way')
        nodes=list(index[('way',m['ref'])]['nodes'])
        if len(nodes)<2: raise ValueError('Short multipolygon member')
        remaining.append((position,m['ref'],nodes))
    rings=[]
    while remaining:
        position,way,nodes=remaining.pop(0)
        chain=list(nodes); pieces=[{'member_index':position,'way_id':way,'reversed':False}]
        while chain[-1]!=chain[0]:
            candidates=[(i,p,w,ns) for i,(p,w,ns) in enumerate(remaining) if ns[0]==chain[-1] or ns[-1]==chain[-1]]
            if len(candidates)!=1: raise ValueError('Unclosed or branching multipolygon member chain')
            i,p,w,ns=candidates[0]; remaining.pop(i)
            reverse=ns[0]!=chain[-1]
            chain.extend((list(reversed(ns)) if reverse else ns)[1:])
            pieces.append({'member_index':p,'way_id':w,'reversed':reverse})
        if len(chain)<4: raise ValueError('Degenerate ring')
        rings.append({'node_ids':chain,'pieces':pieces})
    return rings

def polygon_from_rings(outers, inners, xy):
    shells=[checked(Polygon([xy[n] for n in r['node_ids']]),'outer ring') for r in outers]
    holes=[checked(Polygon([xy[n] for n in r['node_ids']]),'inner ring') for r in inners]
    assignments={i:[] for i in range(len(shells))}
    for r,p in zip(inners,holes):
        containers=[i for i,s in enumerate(shells) if s.contains(p)]
        if len(containers)!=1: raise ValueError('Inner ring lacks unique containing outer ring')
        assignments[containers[0]].append(r)
    parts=[Polygon([xy[n] for n in r['node_ids']],[[xy[n] for n in h['node_ids']] for h in assignments[i]]) for i,r in enumerate(outers)]
    if not parts: raise ValueError('Multipolygon has no outer rings')
    return checked(parts[0] if len(parts)==1 else MultiPolygon(parts),'multipolygon')

def osm_geometries(elements, xy):
    index={(e['type'],e['id']):e for e in elements}; geoms={}; rings={}; active=set()
    if len(index)!=len(elements): raise ValueError('Duplicate OSM type/ID')
    for e in elements:
        if e['type']=='node': geoms[sid(e)]=checked(Point(xy[e['id']]),sid(e))
        elif e['type']=='way':
            pts=[xy[n] for n in e['nodes']]; t=e.get('tags',{})
            if len(pts)<2: raise ValueError(f'Short way {sid(e)}')
            closed=e['nodes'][0]==e['nodes'][-1]
            area=t.get('area')!='no' and (t.get('area')=='yes' or t.get('building') not in (None,'no') or 'landuse' in t or 'landcover' in t or t.get('natural') in {'wood','scrub','grassland','water','wetland'})
            if area and (not closed or len(pts)<4): raise ValueError(f'Unclosed area way {sid(e)}')
            geoms[sid(e)]=checked(Polygon(pts) if area else LineString(pts),sid(e))
    def relation(e):
        key=sid(e)
        if key in geoms: return geoms[key]
        if key in active: raise ValueError('Cyclic relation geometry; raw graph requires review')
        active.add(key)
        if e.get('tags',{}).get('type')=='multipolygon':
            if any(m['role'] not in ('outer','inner') for m in e['members']): raise ValueError('Ambiguous multipolygon role')
            outer=assemble_rings([(i,m) for i,m in enumerate(e['members']) if m['role']=='outer'],index)
            inner=assemble_rings([(i,m) for i,m in enumerate(e['members']) if m['role']=='inner'],index)
            geoms[key]=polygon_from_rings(outer,inner,xy); rings[key]={'outer':outer,'inner':inner}
        else:
            parts=[]
            for m in e['members']:
                child=index[(m['type'],m['ref'])]
                parts.append(relation(child) if child['type']=='relation' else geoms[sid(child)])
            geoms[key]=checked(GeometryCollection(parts),key)
        active.remove(key)
        return geoms[key]
    for e in elements:
        if e['type']=='relation': relation(e)
    return geoms,rings

def nys_geometry(feature):
    rings=feature['geometry']['rings']; shells=[]; holes=[]
    for i,r in enumerate(rings):
        if len(r)<4 or r[0]!=r[-1]: raise ValueError('NYS ring is not closed')
        p=checked(Polygon([(v[0],v[1]) for v in r]),'NYS ring')
        (holes if p.exterior.is_ccw else shells).append((i,r,p))
    parts=[]; used=[]; ring_map=[]
    for i,r,p in shells:
        owned=[(j,h) for j,h,q in holes if p.contains(q)]
        used.extend(j for j,h in owned)
        parts.append(Polygon([(v[0],v[1]) for v in r], [[(v[0],v[1]) for v in h] for j,h in owned]))
        ring_map.append({'outer_ring_index':i,'inner_ring_indices':[j for j,h in owned]})
    if sorted(used)!=sorted(j for j,r,p in holes): raise ValueError('NYS holes unassigned or multiply assigned')
    if not parts: raise ValueError('No NYS outer ring')
    return checked(parts[0] if len(parts)==1 else MultiPolygon(parts),'NYS footprint'),ring_map

def scope(g, region):
    if region.covers(g): return 'inside'
    if not region.intersects(g): return 'outside_dependency'
    if g.touches(region): return 'boundary_touching'
    return 'boundary_crossing'

def json_geometry(g):
    return json.loads(json.dumps(mapping(g)))

def collection(source,features):
    return {'schema':SCHEMA,'crs':CRS,'units':'metre','local_origin_offset':[0,0],
            'source':source,'format_note':'Projected JSON feature layer; NOT RFC 7946 GeoJSON.',
            'features':sorted(features,key=lambda f:f['id'])}

def review_record(identifier,g,state,layers,tags):
    return {'id':identifier,'scope':state,'layers':layers,'bounds':list(g.bounds),
            'source_name':tags.get('name'),'semantics':{k:v for k,v in tags.items() if k in SEMANTICS},
            'decision':'retain_complete_feature_and_all_graph_dependencies',
            'reason':'Do not introduce cut vertices, split source ways, discard relation members, or infer connections across levels.'}
