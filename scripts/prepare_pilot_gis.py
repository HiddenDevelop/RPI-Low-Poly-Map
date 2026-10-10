"""Build deterministic, source-preserving pilot layers in a NEW directory.

Usage: python scripts/prepare_pilot_gis.py [--output gis/cleaned/pilot]
No clipping, snapping, repair, source merge, raster conversion, or Blender work.
"""
import argparse
from collections import Counter
from pathlib import Path

import shapely
from shapely.geometry import Polygon, box
from pilot_gis import (ROOT,RAW,LAYERS,SEMANTICS,CRS,read,encoded,sha,verify_raw,sid,
    transformer,operation_record,osm_geometries,nys_geometry,scope,classifications,
    collection,json_geometry,review_record)

def build():
    hashes=verify_raw()
    area=read(ROOT/'gis/pilot_area.json')
    if area!=read(RAW/'sources.json')['pilot']:
        raise ValueError('Pilot selection differs from sealed acquisition; explicit review required')
    t=transformer(); osm=read(RAW/'osm/pilot.json')
    elements=sorted(osm['elements'],key=lambda e:(e['type'],e['id']))
    wgs={e['id']:(e['lon'],e['lat']) for e in elements if e['type']=='node'}
    projected={n:t.transform(*p,errcheck=True) for n,p in sorted(wgs.items())}
    native_geoms,_=osm_geometries(elements,wgs)
    geoms,rings=osm_geometries(elements,projected)
    region=box(*area['bbox_wgs84'])
    # Densify only the analytical AOI boundary; source geometry is never densified.
    corners=list(region.exterior.coords); border=[]
    for a,b in zip(corners,corners[1:]):
        border.extend(t.transform(a[0]+(b[0]-a[0])*i/32,a[1]+(b[1]-a[1])*i/32) for i in range(32))
    projected_region=Polygon(border)
    layers={k:[] for k in LAYERS}; graph=[]; edges=[]; boundaries=[]; outside=[]
    for e in elements:
        key=sid(e); g=geoms[key]; state=scope(native_geoms[key],region); tags=e.get('tags',{})
        record={'id':key,'source':e,'scope':state}
        if e['type']=='node': record['xy']=list(projected[e['id']])
        if key in rings: record['assembled_ring_provenance']=rings[key]
        graph.append(record)
        if e['type']=='way':
            edges.extend({'way_id':key,'segment_index':i,'from_node_id':a,'to_node_id':b}
                         for i,(a,b) in enumerate(zip(e['nodes'],e['nodes'][1:])))
        assigned=classifications(e)
        if state=='outside_dependency': outside.append(key)
        else:
            feature={'id':key,'geometry':json_geometry(g),'source':e,
                     'scope':state,'semantics':{k:v for k,v in tags.items() if k in SEMANTICS}}
            if key in rings: feature['assembled_ring_provenance']=rings[key]
            for layer in assigned: layers[layer].append(feature)
        if state.startswith('boundary_'):
            boundaries.append(review_record(key,g,state,assigned,tags))
    nys=read(RAW/'nys/pilot_buildings.json')
    if nys.get('exceededTransferLimit') or nys['spatialReference'].get('latestWkid',nys['spatialReference'].get('wkid'))!=26918:
        raise ValueError('NYS response truncated or CRS unexpected')
    nys_features=[]
    for f in sorted(nys['features'],key=lambda f:f['attributes']['OBJECTID']):
        key=f"nys/building/{f['attributes']['OBJECTID']}"; g,ringmap=nys_geometry(f)
        state=scope(g,projected_region)
        nys_features.append({'id':key,'source':f,'geometry':json_geometry(g),'scope':state,
                             'ring_provenance':ringmap,'vertical_status':'source Z preserved in source.geometry only; units/datum unknown'})
        if state.startswith('boundary_'):
            boundaries.append(review_record(key,g,state,['nys_buildings'],{}))
    counts={name:len(features) for name,features in layers.items()}
    files={f'osm/{name}.json':collection('OpenStreetMap',features) for name,features in layers.items()}
    files['osm/source_graph.json']={'schema':'rpi-osm-source-graph-v1','crs':CRS,'units':'metre',
         'original_header':{k:v for k,v in osm.items() if k!='elements'},'elements':graph,
         'way_segments':edges,'routing_status':'Not a routing graph. Segments preserve each ordered source pair including repeats. No coordinate-based merging or level inference.'}
    files['nys/buildings.json']=collection('NYS ITS Geospatial Services / NYSERDA',nys_features)
    files['datum_operations.json']=operation_record(area['bbox_wgs84'])
    files['boundary_review.json']={'pilot_wgs84':area['bbox_wgs84'],'osm_scope_method':'Exact original WGS84 geometry versus acquisition envelope; no clipping',
         'nys_scope_method':'Native EPSG:26918 geometry versus AOI boundary transformed with 32 subdivisions per side',
         'bounds_crs':CRS,'policy':'Retain all intersecting source features whole; retain outside graph dependencies separately. Do not crop on import without a new reviewed policy.',
         'features':sorted(boundaries,key=lambda r:r['id']),'outside_dependency_ids':sorted(outside),
         'scope_counts':dict(sorted(Counter(r['scope'] for r in graph).items())),
         'relation_review':[{'id':r['id'],'scope':r['scope'],'member_count':len(r['source']['members']),
                            'decision':'Keep every member occurrence, original order and role, including repeated members.'} for r in graph if r['source']['type']=='relation']}
    selected=read(RAW/'sources.json')['selected_elevation']
    files['terrain_reference.json']={'source':f'gis/raw/{selected}','sha256':hashes[selected],
        'crs':CRS,'vertical_datum':'NAVD88','vertical_units':'metre','operation':'none',
        'status':'Reference only; raster not copied, clipped, resampled or draped onto vectors.',
        'limitations':'Does not resolve multilevel paths; campus acquisition date and achieved vertical accuracy remain unconfirmed.'}
    files['processing_log.json']={'input_osm_counts':dict(sorted(Counter(e['type'] for e in elements).items())),
        'output_graph_counts':dict(sorted(Counter(r['source']['type'] for r in graph).items())),
        'pilot_layer_counts':counts,'nys_input_count':len(nys['features']),'nys_output_count':len(nys_features),
        'discarded_invalid_features':0,'repairs':[],'clipped_features':0,'merged_features':0,
        'input_crs':{'osm':'EPSG:4326','nys':CRS},'output_crs':CRS,
        'input_osm_bounds':list(GeometryBounds(native_geoms)), 'output_osm_bounds':list(GeometryBounds(geoms)),
        'layer_bounds':{k:list(GeometryBounds({str(i):shapely.geometry.shape(f['geometry']) for i,f in enumerate(v)})) if v else None for k,v in layers.items()},
        'metadata_policy':'All original source records retained exactly as JSON values. Missing tags remain absent. Derived semantics copy only present strings; no parsed or inferred levels/accessibility.',
        'determinism':'Sorted source IDs and dictionary keys; original node/member/ring order preserved. No run timestamps, random values, or absolute file paths.'}
    files['manifest.json']={'schema':'rpi-pilot-manifest-v1','output_crs':CRS,'units':'metre',
        'raw_seal_sha256':sha(RAW/'SHA256SUMS.txt'),'raw_files_verified':len(hashes),
        'input_hashes':{name:hashes[name] for name in ['osm/pilot.json','nys/pilot_buildings.json','sources.json',selected]},
        'pilot':area,'pilot_area_sha256':sha(ROOT/'gis/pilot_area.json'),
        'code_hashes':{f'scripts/{name}':sha(ROOT/'scripts'/name) for name in ['pilot_gis.py','prepare_pilot_gis.py','validate_pilot_gis.py']},
        'versions':{'shapely':shapely.__version__},'source_policy':'OSM and NYS remain separate; no fusion',
        'validation_scope':'Source fidelity and derived layer consistency only; not proof of accessibility, survey accuracy, routing safety or Blender import readiness.',
        'file_sha256':{name:__import__('hashlib').sha256(encoded(value)).hexdigest() for name,value in sorted(files.items())}}
    return files

def GeometryBounds(geoms):
    bounds=[g.bounds for g in geoms.values()]
    return min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'gis/cleaned/pilot')
    a=parser.parse_args(); output=a.output.resolve()
    if not output.is_relative_to((ROOT/'gis/cleaned').resolve()) or output==(ROOT/'gis/cleaned').resolve():
        raise ValueError('Output must be a new subdirectory of gis/cleaned')
    if output.exists(): raise FileExistsError(f'Refusing overwrite: {output}')
    files=build()
    # Validate in memory before writing; validation reads raw inputs independently.
    from validate_pilot_gis import validate_values
    report=validate_values(files)
    if not report['passed']: raise ValueError(report)
    files['validation.json']=report
    output.mkdir(parents=True,exist_ok=False)
    for name,value in sorted(files.items()):
        dest=output/name; dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f: f.write(encoded(value))
    verify_raw()
    print(f'Created {len(files)} deterministic files in {output}; validation passed.')

if __name__=='__main__': main()
