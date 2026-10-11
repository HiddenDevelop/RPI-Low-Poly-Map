"""Independent source/topology/unknown-value checks for the navigation review."""
import hashlib
import json
from pathlib import Path
from collections import defaultdict
from shapely.geometry import shape

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'gis/cleaned/rpi_navigation_20261011_pass04'

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    doc=read(OUT/'features.json');top=read(OUT/'source_topology.json');roi=shape(doc['aoi'])
    source={f['id']:f for name in ['paths','stairs','entrances','accessibility']
            for f in read(ROOT/f'gis/cleaned/pilot/osm/{name}.json')['features'] if shape(f['geometry']).intersects(roi)}
    assert set(source)=={r['id'] for r in doc['records']}
    expected=[];incidence=defaultdict(list)
    for r in doc['records']:
        f=source[r['id']];tags=f['source'].get('tags',{})
        assert r['feature']==f, 'Complete source record changed'
        assert r['wheelchair']==tags.get('wheelchair')
        assert r['surface']==tags.get('surface')
        assert r['level']==tags.get('level') and r['layer']==tags.get('layer')
        assert r['routing_eligibility']=='not_validated'
        if f['geometry']['type']!='LineString':continue
        nodes=f['source']['nodes'];coords=f['geometry']['coordinates']
        for i,n in enumerate(nodes):
            incidence[str(n)].append({'source_id':f['id'],'index':i,'level':tags.get('level'),'layer':tags.get('layer')})
        for i,(a,b) in enumerate(zip(nodes,nodes[1:])):
            expected.append((f['id'],i,a,b,coords[i:i+2]))
    actual=[(e['source_id'],e['index'],e['from_node'],e['to_node'],e['xy']) for e in top['segments']]
    assert expected==actual and dict(incidence)==top['node_incidence']
    for crossing in top['geometric_crossing_review']:
        a,b=[source[k] for k in crossing['source_ids']]
        assert not set(a['source']['nodes'])&set(b['source']['nodes'])
        assert shape(a['geometry']).intersection(shape(b['geometry'])).equals(shape(crossing['geometry']))
    for name,digest in read(OUT/'manifest.json')['files'].items():
        assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest
    for tree in read(OUT/'landscape_review.json')['trees']:assert tree['routing_obstacle'] is None
    result={'passed':True,'source_features_exact':len(source),'ordered_segments_exact':len(actual),
            'ordered_node_incidence_exact':len(incidence),'source_accessibility_unknowns_preserved':True,
            'source_crs':'EPSG:26918','navigation_ready':False}
    p=OUT/'independent_validation.json'
    if p.exists():assert read(p)==result
    else:
        with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
