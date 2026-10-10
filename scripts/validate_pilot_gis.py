"""Fail-loud, read-only validation against immutable raw source records.

Checks source identity/attributes, ordered graph topology, all coordinates,
relation ring provenance, layer completeness, boundary review, CRS, hashes,
and missing/empty/invalid/degenerate geometry. Does not fix any data.
"""
import argparse
import hashlib
import math
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection, box
from shapely.validation import explain_validity
from pilot_gis import (ROOT,RAW,SCHEMA,CRS,PIPELINE,LAYERS,SEMANTICS,read,encoded,
    sha,verify_raw,sid,classifications,transformer,json_geometry,scope,review_record,operation_record)

class ValidationError(ValueError): pass

def require(ok,message):
    if not ok: raise ValidationError(message)

def close_coordinates(actual,expected,label,tolerance=1e-6):
    require(type(actual)==type(expected) or isinstance(actual,(list,tuple)) and isinstance(expected,(list,tuple)), f'{label}: coordinate structure mismatch')
    if isinstance(expected,(list,tuple)):
        require(len(actual)==len(expected),f'{label}: coordinate/vertex count mismatch')
        for a,b in zip(actual,expected): close_coordinates(a,b,label,tolerance)
    else:
        require(isinstance(actual,(int,float)) and math.isfinite(actual) and abs(actual-expected)<=tolerance,f'{label}: coordinate shift/nonfinite value')

def compare_geometry(actual,expected,label):
    require(actual['type']==expected['type'],f'{label}: geometry type changed')
    if actual['type']=='GeometryCollection':
        require(len(actual['geometries'])==len(expected['geometries']),f'{label}: relation member geometry count changed')
        for a,b in zip(actual['geometries'],expected['geometries']): compare_geometry(a,b,label)
    else: close_coordinates(actual['coordinates'],expected['coordinates'],label)
    g=shape(actual)
    require(not g.is_empty and g.is_valid,f'{label}: invalid/empty geometry {explain_validity(g)}')
    if g.geom_type in ('Polygon','MultiPolygon'): require(g.area>1e-9,f'{label}: zero-area footprint')
    if g.geom_type=='LineString': require(g.length>1e-9,f'{label}: zero-length path')
    require(all(math.isfinite(x) for x in g.bounds),f'{label}: nonfinite bounds')
    require(580000<g.bounds[0]<=g.bounds[2]<630000 and 4710000<g.bounds[1]<=g.bounds[3]<4750000,f'{label}: outside expected greater-Troy source bounds')

def source_geometry(e,xy,index,graph,native=False,active=None):
    """Reconstruct expectations from raw ordered references, not parser output."""
    key=sid(e); active=set() if active is None else active
    require(key not in active,'Cyclic source relation')
    if e['type']=='node': return {'type':'Point','coordinates':list(xy[e['id']])}
    if e['type']=='way':
        pts=[list(xy[n]) for n in e['nodes']]; t=e.get('tags',{})
        is_area=t.get('area')!='no' and (t.get('area')=='yes' or t.get('building') not in (None,'no') or 'landuse' in t or 'landcover' in t or t.get('natural') in {'wood','scrub','grassland','water','wetland'})
        require(not is_area or e['nodes'][0]==e['nodes'][-1],f'{key}: unclosed area')
        return {'type':'Polygon','coordinates':[pts]} if is_area else {'type':'LineString','coordinates':pts}
    active=active|{key}
    if e.get('tags',{}).get('type')!='multipolygon':
        return {'type':'GeometryCollection','geometries':[source_geometry(index[(m['type'],m['ref'])],xy,index,graph,native,active) for m in e['members']]}
    provenance=graph[key]['assembled_ring_provenance']; used=[]; rings={}
    for role in ('outer','inner'):
        rings[role]=[]
        for ring in provenance[role]:
            chain=[]
            for piece in ring['pieces']:
                pos=piece['member_index']; require(isinstance(pos,int) and 0<=pos<len(e['members']),f'{key}: bad member index')
                member=e['members'][pos]; used.append(pos)
                require(member=={'type':'way','ref':piece['way_id'],'role':role},f'{key}: ring role/member changed')
                nodes=list(index[('way',member['ref'])]['nodes'])
                require(isinstance(piece['reversed'],bool),f'{key}: ambiguous orientation')
                if piece['reversed']: nodes.reverse()
                require(not chain or chain[-1]==nodes[0],f'{key}: joined distinct source nodes')
                chain.extend(nodes if not chain else nodes[1:])
            require(chain==ring['node_ids'] and len(chain)>=4 and chain[0]==chain[-1],f'{key}: altered ring node sequence')
            rings[role].append([list(xy[n]) for n in chain])
    require(sorted(used)==list(range(len(e['members']))),f'{key}: missing/duplicate ring member occurrence')
    parts=[]; assigned=[]
    for outer in rings['outer']:
        shell=Polygon(outer); holes=[]
        for i,inner in enumerate(rings['inner']):
            if shell.contains(Polygon(inner)): holes.append(inner); assigned.append(i)
        parts.append([outer]+holes)
    require(sorted(assigned)==list(range(len(rings['inner']))),f'{key}: hole ownership invalid')
    require(bool(parts),f'{key}: no outer ring')
    return {'type':'Polygon','coordinates':parts[0]} if len(parts)==1 else {'type':'MultiPolygon','coordinates':parts}

def validate_values(files):
    checks=[]
    try:
        raw_hashes=verify_raw(); checks.append('raw integrity seal')
        manifest=files['manifest.json']; require(manifest['schema']=='rpi-pilot-manifest-v1','Manifest schema')
        expected_names={f'osm/{n}.json' for n in LAYERS}|{'osm/source_graph.json','nys/buildings.json','datum_operations.json','boundary_review.json','terrain_reference.json','processing_log.json'}
        require(set(files)-{'manifest.json','validation.json'}==expected_names,'Missing or unexpected output files')
        require(set(manifest['file_sha256'])==expected_names,'Incomplete derived hash manifest')
        for name,digest in manifest['file_sha256'].items():
            require(hashlib.sha256(encoded(files[name])).hexdigest()==digest,f'Derived hash mismatch: {name}')
        require(manifest['output_crs']==CRS and manifest['units']=='metre','Manifest CRS/units')
        require(manifest['raw_seal_sha256']==sha(RAW/'SHA256SUMS.txt'),'Raw seal changed')
        selected=read(RAW/'sources.json')['selected_elevation']
        require(set(manifest['input_hashes'])=={'osm/pilot.json','nys/pilot_buildings.json','sources.json',selected},'Incomplete source provenance')
        require(set(manifest['code_hashes'])=={'scripts/pilot_gis.py','scripts/prepare_pilot_gis.py','scripts/validate_pilot_gis.py'},'Incomplete code provenance')
        for name,digest in manifest['input_hashes'].items(): require(raw_hashes[name]==digest,f'Input changed: {name}')
        for name,digest in manifest['code_hashes'].items(): require(sha(ROOT/name)==digest,f'Pipeline code changed: {name}')
        area=read(ROOT/'gis/pilot_area.json')
        require(area==manifest['pilot']==read(RAW/'sources.json')['pilot'],'Unreviewed pilot change')
        require(sha(ROOT/'gis/pilot_area.json')==manifest['pilot_area_sha256'],'Pilot file changed')
        operation=files['datum_operations.json']
        require(operation['pipeline']==PIPELINE and operation['output_crs']==CRS and operation['input_crs']=='EPSG:4326','Datum operation mismatch')
        require(operation['stated_operation_accuracy_m']==4.0 and operation['grids_used']==[] and operation['network_enabled'] is False and operation['ballpark_allowed'] is False,'Datum uncertainty/settings altered')
        require(operation['local_origin_offset']==[0,0] and operation['units']=='metre','Offset/units changed')
        import pyproj
        require(operation['proj_database_sha256']==sha(Path(pyproj.datadir.get_data_dir())/'proj.db'),'PROJ database changed')
        require(operation==operation_record(area['bbox_wgs84']),'Datum operation description or environment changed')
        checks.append('input/output hashes and documented datum operation')
        osm=read(RAW/'osm/pilot.json'); elements=osm['elements']; index={(e['type'],e['id']):e for e in elements}
        require(len(index)==len(elements),'Duplicate source OSM IDs')
        graph_file=files['osm/source_graph.json']; records=graph_file['elements']; graph={r['id']:r for r in records}
        require(graph_file['crs']==CRS and graph_file['units']=='metre','Graph CRS/units')
        require(graph_file['schema']=='rpi-osm-source-graph-v1','Graph schema')
        require(len(graph)==len(records)==len(elements) and set(graph)=={sid(e) for e in elements},'Lost/duplicate graph elements')
        require(graph_file['original_header']=={k:v for k,v in osm.items() if k!='elements'},'OSM header changed')
        t=transformer(); wgs={e['id']:(e['lon'],e['lat']) for e in elements if e['type']=='node'}
        xy={n:t.transform(*p,errcheck=True) for n,p in wgs.items()}
        for e in elements:
            key=sid(e); record=graph[key]
            require(record['source']==e,f'{key}: source tags, metadata, nodes or ordered members changed')
            extra={'xy'} if e['type']=='node' else ({'assembled_ring_provenance'} if e.get('tags',{}).get('type')=='multipolygon' else set())
            require(set(record)=={'id','source','scope'}|extra,f'{key}: unexpected graph attributes')
            if e['type']=='node':
                close_coordinates(record['xy'],list(xy[e['id']]),key)
                inverse=t.transform(*record['xy'],direction='INVERSE',errcheck=True)
                close_coordinates(list(inverse),list(wgs[e['id']]),f'{key} inverse',1e-9)
            elif e['type']=='way':
                require(all(n in wgs for n in e['nodes']),f'{key}: dangling node')
            else:
                require(all((m['type'],m['ref']) in index for m in e['members']),f'{key}: dangling member')
        expected_edges=[{'way_id':sid(e),'segment_index':i,'from_node_id':a,'to_node_id':b}
                        for e in sorted(elements,key=lambda e:(e['type'],e['id'])) if e['type']=='way'
                        for i,(a,b) in enumerate(zip(e['nodes'],e['nodes'][1:]))]
        require(graph_file['way_segments']==expected_edges,'Ordered way segments/topology changed')
        checks.append('all raw records, ordered node/member lists, roles, repeated members and source segments')
        region=box(*area['bbox_wgs84']); expected={}; native={}; states={}; expected_membership={n:set() for n in LAYERS}; boundaries=[]
        for e in elements:
            key=sid(e)
            expected[key]=source_geometry(e,xy,index,graph)
            native[key]=shape(source_geometry(e,wgs,index,graph,True))
            state=scope(native[key],region); states[key]=state
            require(graph[key]['scope']==state,f'{key}: wrong boundary classification')
            compare_geometry(expected[key],expected[key],key)
            if state!='outside_dependency':
                for n in classifications(e): expected_membership[n].add(key)
            if state.startswith('boundary_'): boundaries.append(review_record(key,shape(expected[key]),state,classifications(e),e.get('tags',{})))
        for name in LAYERS:
            layer=files[f'osm/{name}.json']
            require(layer['schema']==SCHEMA and layer['crs']==CRS and layer['units']=='metre' and layer['local_origin_offset']==[0,0],f'{name}: invalid layer CRS/units/schema')
            features=layer['features']; ids=[f['id'] for f in features]
            require(len(ids)==len(set(ids)) and set(ids)==expected_membership[name],f'{name}: missing/extra/duplicate feature IDs')
            require(ids==sorted(ids),f'{name}: unstable order')
            for f in features:
                key=f['id']; e=graph[key]['source']; tags=e.get('tags',{})
                allowed={'id','geometry','source','scope','semantics'}|({'assembled_ring_provenance'} if key in graph and 'assembled_ring_provenance' in graph[key] else set())
                require(set(f)==allowed,f'{key}: unexpected fields / possible accessibility inference')
                require(f['source']==e and f['scope']==states[key],f'{key}: metadata/scope mismatch')
                require(f['semantics']=={k:v for k,v in tags.items() if k in SEMANTICS},f'{key}: multilevel/accessibility semantics changed')
                if 'assembled_ring_provenance' in f: require(f['assembled_ring_provenance']==graph[key]['assembled_ring_provenance'],f'{key}: ring provenance mismatch')
                compare_geometry(f['geometry'],expected[key],key)
        checks.append('layer completeness, source IDs, all projected vertices, inverse transforms, geometry validity and multilevel semantics')
        nys=read(RAW/'nys/pilot_buildings.json'); layer=files['nys/buildings.json']; original={f"nys/building/{f['attributes']['OBJECTID']}":f for f in nys['features']}
        require(len(original)==len(nys['features']),'Duplicate NYS source IDs')
        require(layer['schema']==SCHEMA and layer['crs']==CRS and layer['units']=='metre' and layer['local_origin_offset']==[0,0],'NYS CRS/units/schema')
        ids=[f['id'] for f in layer['features']]; require(len(ids)==len(set(ids)) and set(ids)==set(original),'NYS missing/extra/duplicate features')
        corners=list(region.exterior.coords); border=[]
        for a,b in zip(corners,corners[1:]): border.extend(t.transform(a[0]+(b[0]-a[0])*i/32,a[1]+(b[1]-a[1])*i/32) for i in range(32))
        projected_region=Polygon(border)
        for f in layer['features']:
            key=f['id']; raw=original[key]; require(f['source']==raw,f'{key}: NYS native coordinates, Z or attributes altered')
            require(set(f)=={'id','source','geometry','scope','ring_provenance','vertical_status'},f'{key}: unexpected NYS attributes')
            require(f['vertical_status']=='source Z preserved in source.geometry only; units/datum unknown',f'{key}: NYS height assumption introduced')
            rings=raw['geometry']['rings']; parts=[]; used=[]
            for part in f['ring_provenance']:
                indices=[part['outer_ring_index']]+part['inner_ring_indices']; used.extend(indices)
                coords=[[[p[0],p[1]] for p in rings[i]] for i in indices]
                require(not Polygon(coords[0]).exterior.is_ccw,f'{key}: incorrect NYS shell orientation')
                for hole in coords[1:]: require(Polygon(hole).exterior.is_ccw and Polygon(coords[0]).contains(Polygon(hole)),f'{key}: hole association changed')
                parts.append(coords)
            require(sorted(used)==list(range(len(rings))),f'{key}: NYS ring omitted/duplicated')
            exp={'type':'Polygon','coordinates':parts[0]} if len(parts)==1 else {'type':'MultiPolygon','coordinates':parts}
            compare_geometry(f['geometry'],exp,key)
            state=scope(shape(exp),projected_region); require(state==f['scope'],f'{key}: NYS boundary classification')
            if state.startswith('boundary_'): boundaries.append(review_record(key,shape(exp),state,['nys_buildings'],{}))
        checks.append('NYS isolated, all native XY/Z/attributes and rings retained')
        review=files['boundary_review.json']
        require(review['features']==sorted(boundaries,key=lambda r:r['id']),'Boundary-crossing review incomplete/altered')
        require(review['outside_dependency_ids']==sorted(k for k,v in states.items() if v=='outside_dependency'),'Outside dependencies dropped')
        require(review['scope_counts']==dict(Counter(states.values())),'Scope counts wrong')
        require(review['pilot_wgs84']==area['bbox_wgs84'] and review['bounds_crs']==CRS,'Boundary review CRS/bounds changed')
        expected_relations=[{'id':r['id'],'scope':r['scope'],'member_count':len(r['source']['members']),
              'decision':'Keep every member occurrence, original order and role, including repeated members.'} for r in records if r['source']['type']=='relation']
        require(review['relation_review']==expected_relations,'Relation review incomplete')
        for b in area['buildings']:
            key=f"osm/{b['osm_type']}/{b['osm_id']}"
            require(key in expected_membership['buildings'] and states[key]=='inside',f'Target footprint missing or truncated: {key}')
        terrain=files['terrain_reference.json']; selected=read(RAW/'sources.json')['selected_elevation']
        require(terrain['source']==f'gis/raw/{selected}' and terrain['sha256']==raw_hashes[selected] and terrain['operation']=='none','Terrain reference modified')
        log=files['processing_log.json']
        require(log['input_osm_counts']==log['output_graph_counts']==dict(Counter(e['type'] for e in elements)),'Graph count logging wrong')
        require(log['pilot_layer_counts']=={n:len(expected_membership[n]) for n in LAYERS},'Layer counts wrong')
        require(log['nys_input_count']==log['nys_output_count']==len(original),'NYS counts wrong')
        require(log['discarded_invalid_features']==log['clipped_features']==log['merged_features']==0 and log['repairs']==[],'Unexpected repair/drop/clip policy')
        require(log['input_crs']=={'osm':'EPSG:4326','nys':CRS} and log['output_crs']==CRS,'Log CRS incorrect')
        def bounds_of(gs):
            b=[g.bounds for g in gs]
            return [min(x[0] for x in b),min(x[1] for x in b),max(x[2] for x in b),max(x[3] for x in b)] if b else None
        close_coordinates(log['input_osm_bounds'],bounds_of(native.values()),'Input bounds',1e-12)
        close_coordinates(log['output_osm_bounds'],bounds_of(shape(g) for g in expected.values()),'Output bounds')
        for n in LAYERS:
            expected_bounds=bounds_of(shape(expected[k]) for k in expected_membership[n])
            if expected_bounds is None: require(log['layer_bounds'][n] is None,'Empty layer bounds')
            else: close_coordinates(log['layer_bounds'][n],expected_bounds,f'{n} bounds')
        checks.append('all seven target buildings, boundary review, outside dependencies and terrain reference')
        return {'passed':True,'checks':checks,'raw_files_verified':len(raw_hashes),'source_graph_elements':len(elements),
                'source_way_segments':len(expected_edges),'layer_counts':log['pilot_layer_counts'],
                'nys_buildings':len(original),'boundary_review_count':len(boundaries),
                'coordinate_tolerance_m':1e-6,'inverse_tolerance_degrees':1e-9,
                'limitations':['4 m stated datum-operation accuracy is not source positional accuracy.',
                    'No routing/accessibility or Blender validation performed.','No source geometry repaired, clipped or merged.']}
    except (ValueError,KeyError,TypeError,IndexError,OSError) as exc:
        return {'passed':False,'checks_completed':checks,'error':f'{type(exc).__name__}: {exc}'}

def validate_directory(path):
    path=Path(path)
    values={p.relative_to(path).as_posix():read(p) for p in path.rglob('*.json')}
    if 'manifest.json' in values:
        for name,digest in values['manifest.json']['file_sha256'].items():
            candidate=(path/name).resolve()
            require(candidate.is_relative_to(path.resolve()),'Derived manifest path escapes output directory')
            require(sha(candidate)==digest,f'Derived file bytes changed: {name}')
    result=validate_values(values)
    if result['passed'] and 'validation.json' in values:
        require(values['validation.json']==result,'Saved validation report does not match recomputation')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('directory',nargs='?',type=Path,default=ROOT/'gis/cleaned/pilot')
    args=p.parse_args()
    try: result=validate_directory(args.directory)
    except Exception as exc: result={'passed':False,'error':f'{type(exc).__name__}: {exc}'}
    print(encoded(result).decode(),end='')
    if not result['passed']: raise SystemExit(1)

if __name__=='__main__': main()
