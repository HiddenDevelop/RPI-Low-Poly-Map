"""Derive a WGS84 acquisition envelope from seven discovered OSM footprints."""
import json
import math
from pyproj import Geod
from acquire_public_gis import ROOT, RAW, write_new

NAMES = ['Darrin Communications Center', 'J Erik Jonsson Engineering Center',
         'Folsom Library', 'Greene Building', 'Amos Eaton Hall', 'Lally Hall',
         'Rensselaer Student Union']
data = json.loads((RAW/'osm/discovery.json').read_text())
selected = []
for name in NAMES:
    found = [e for e in data['elements'] if e.get('tags',{}).get('name') == name]
    if len(found) != 1 or found[0]['type'] != 'way' or found[0]['nodes'][0] != found[0]['nodes'][-1]:
        raise RuntimeError(f'Ambiguous or non-closed footprint: {name}')
    selected.append(found[0])
pts = [p for e in selected for p in e['geometry']]
w,e = min(p['lon'] for p in pts), max(p['lon'] for p in pts)
s,n = min(p['lat'] for p in pts), max(p['lat'] for p in pts)
geod = Geod(ellps='WGS84')
margin = 50
w = geod.fwd(w,(s+n)/2,270,margin)[0]
e = geod.fwd(e,(s+n)/2,90,margin)[0]
s = geod.fwd((w+e)/2,s,180,margin)[1]
n = geod.fwd((w+e)/2,n,0,margin)[1]
box = [math.floor(w*1e6)/1e6,math.floor(s*1e6)/1e6,math.ceil(e*1e6)/1e6,math.ceil(n*1e6)/1e6]
result = {'bbox_wgs84':box,'bbox_order':'west,south,east,north','crs':'EPSG:4326',
          'method':'Envelope of complete OSM footprints for seven exact-name matches; 50 m geodesic outward margin, rounded outward to 6 decimals. Acquisition selection only; no geometry clipped.',
          'osm_snapshot_utc':data['osm3s']['timestamp_osm_base'],
          'buildings':[{'name':e['tags']['name'],'osm_type':e['type'],'osm_id':e['id'],'bounds':e['bounds']} for e in selected],
          'width_m':geod.inv(box[0],(box[1]+box[3])/2,box[2],(box[1]+box[3])/2)[2],
          'height_m':geod.inv((box[0]+box[2])/2,box[1],(box[0]+box[2])/2,box[3])[2]}
write_new(ROOT/'gis/pilot_area.json',json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
