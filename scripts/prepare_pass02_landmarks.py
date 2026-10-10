"""Prepare reference-inspired display roofs, clipped to unchanged source footprints.

Run with .local/gis-venv/Scripts/python.exe. Dimensions are visual estimates.
No raw/cleaned GIS or earlier Blender artifacts are modified.
"""
import json
import math
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely import affinity
from shapely.ops import triangulate

ROOT = Path(__file__).resolve().parents[1]
RUN = 'rpi_lowpoly_20261010_pass02'
payload = json.loads((ROOT/'blender/working/rpi_lowpoly_20261010_01_payload.json').read_text())
origin = payload['origin_projected_m']
references = {
 'osm/way/104737317': {'kind':'chapel','rise_m':7.0,'strips':2,
   'reference':'https://archives.rpi.edu/institute-history/building-histories/chapel-voorhees-computing-center'},
 'osm/way/262004862': {'kind':'empac','rise_m':4.0,'strips':8,
   'reference':'https://grimshaw.global/projects/education-and-science/empac/'},
 'osm/way/104737293': {'kind':'library','rise_m':0.0,'strips':0,
   'reference':'https://archives.rpi.edu/institute-history/building-histories/folsom-library'},
}
result = {}
for item in payload['features']:
    f = item['feature']
    if f['id'] not in references:
        continue
    info = dict(references[f['id']])
    xy = [(p[0]-origin[0], p[1]-origin[1]) for p in f['geometry']['coordinates'][0][:-1]]
    polygon = Polygon(xy)
    rect = list(polygon.minimum_rotated_rectangle.exterior.coords)
    edges = [(math.dist(a,b),a,b) for a,b in zip(rect,rect[1:])]
    _, a, b = max(edges)
    angle = math.atan2(b[1]-a[1], b[0]-a[0])
    local = affinity.rotate(polygon, -angle, origin=(0,0), use_radians=True)
    xmin,ymin,xmax,ymax = local.bounds
    roof = max(item['ground_center']+item['display_height_m'],max(item['ground_samples'])+4)
    def xyz(x,y):
        t = (y-ymin)/(ymax-ymin)
        rise = info['rise_m']*(1-abs(2*t-1)) if info['kind']=='chapel' else info['rise_m']*4*t*(1-t)
        return [x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle),roof+0.06+rise]
    vertices, faces = [], []
    count = info['strips']
    for i in range(count):
        lo=ymin+(ymax-ymin)*i/count
        hi=ymin+(ymax-ymin)*(i+1)/count
        part=local.intersection(box(xmin-1,lo,xmax+1,hi))
        pieces=[part] if part.geom_type=='Polygon' else list(part.geoms)
        for piece in pieces:
            if piece.geom_type!='Polygon': continue
            for tri in triangulate(piece):
                if not piece.covers(tri): continue
                start=len(vertices)
                vertices.extend(xyz(x,y) for x,y in list(tri.exterior.coords)[:-1])
                faces.append([start,start+1,start+2])
    # Fascia subdivisions include ridge/strip crossings and remain within source XY.
    for a,b in zip(list(local.exterior.coords),list(local.exterior.coords)[1:]):
        cuts=[0.0,1.0]
        if count and b[1]!=a[1]:
            for j in range(1,count):
                t=(ymin+(ymax-ymin)*j/count-a[1])/(b[1]-a[1])
                if 0<t<1:cuts.append(t)
        cuts.sort()
        for lo,hi in zip(cuts,cuts[1:]):
            if not count:continue
            p=xyz(a[0]+(b[0]-a[0])*lo,a[1]+(b[1]-a[1])*lo)
            q=xyz(a[0]+(b[0]-a[0])*hi,a[1]+(b[1]-a[1])*hi)
            start=len(vertices);vertices.extend([[p[0],p[1],roof], [q[0],q[1],roof],q,p])
            faces.append([start,start+1,start+2,start+3])
    assert all(polygon.buffer(1e-7).covers(Polygon([v[:2] for v in [vertices[k] for k in face]]))
               for face in faces if len(set(tuple(vertices[k][:2]) for k in face))>=3)
    info.update(vertices=vertices,faces=faces,source_id=f['id'],name=f['source']['tags']['name'],
                roof_base_m=roof,base_m=item['ground_base'],footprint_xy=xy,
                dimensions_status='Reference-inspired silhouette; roof rise, bays and heights are illustrative, not measured.',
                reference_review_date='2026-10-10')
    result[f['id']]=info
out=ROOT/'blender/working'/f'{RUN}_landmarks.json'
with out.open('x',encoding='utf-8',newline='\n') as handle:
    json.dump(result,handle,sort_keys=True,indent=2)
print(out)
