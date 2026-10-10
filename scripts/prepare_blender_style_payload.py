"""Prepare measured terrain samples for visualization; never edit GIS sources."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import rasterio
from shapely.geometry import shape
from pilot_gis import ROOT, RAW, encoded, read, sha, transformer
from validate_pilot_gis import validate_directory

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run',required=True); a=parser.parse_args()
    if not a.run.replace('_','').replace('-','').isalnum(): raise ValueError('Simple run identifier required')
    out=ROOT/'blender/working'/f'{a.run}_payload.json'
    if out.exists(): raise FileExistsError(out)
    validation=validate_directory(ROOT/'gis/cleaned/pilot')
    if not validation['passed']: raise ValueError(validation)
    names=['buildings','paths','roads','stairs','entrances','accessibility','landcover']
    features={}
    for layer in names:
        for f in read(ROOT/f'gis/cleaned/pilot/osm/{layer}.json')['features']:
            if f['id'] not in features: features[f['id']]={'feature':f,'layers':[]}
            features[f['id']]['layers'].append(layer)
    bounds=[shape(d['feature']['geometry']).bounds for d in features.values()]
    xmin=math.floor((min(b[0] for b in bounds)-15)/4)*4
    ymin=math.floor((min(b[1] for b in bounds)-15)/4)*4
    xmax=math.ceil((max(b[2] for b in bounds)+15)/4)*4
    ymax=math.ceil((max(b[3] for b in bounds)+15)/4)*4
    origin=[math.floor((xmin+xmax)/2/100)*100,math.floor((ymin+ymax)/2/100)*100,0]
    terrain=read(ROOT/'gis/cleaned/pilot/terrain_reference.json')
    raster=ROOT/terrain['source']
    if sha(raster)!=terrain['sha256']: raise ValueError('Terrain hash changed')
    with rasterio.open(raster) as ds:
        def z(x,y):
            row,col=ds.index(x,y)
            value=float(ds.read(1,window=rasterio.windows.Window(col,row,1,1))[0,0])
            if not math.isfinite(value) or value==ds.nodata: raise ValueError(f'Missing DEM at {x},{y}')
            return value
        xs=list(range(xmin,xmax+1,4)); ys=list(range(ymin,ymax+1,4))
        # One window, native nearest-pixel sampling, no reprojection or invented heights.
        window=rasterio.windows.from_bounds(xmin-4,ymin-4,xmax+4,ymax+4,ds.transform).round_offsets().round_lengths()
        array=ds.read(1,window=window)
        tr=ds.window_transform(window)
        def sample(x,y):
            row,col=rasterio.transform.rowcol(tr,x,y); val=float(array[row,col])
            if not math.isfinite(val) or val==ds.nodata: raise ValueError('DEM void in visualization extent')
            return val
        grid=[[float(x-origin[0]),float(y-origin[1]),sample(x,y)] for y in ys for x in xs]
        for key,d in sorted(features.items()):
            f=d['feature']; geom=shape(f['geometry']); t=f['source'].get('tags',{})
            if geom.geom_type=='Polygon':
                coords=f['geometry']['coordinates'][0]
                d['ground_samples']=[sample(p[0],p[1]) for p in coords]
                d['ground_base']=min(d['ground_samples'])-0.5
                d['ground_center']=sample(geom.centroid.x,geom.centroid.y)
                if 'buildings' in d['layers']:
                    try: height=float(t.get('building:levels','3'))*3.4
                    except ValueError: height=10.2
                    d['display_height_m']=max(6,min(height,30))
                    d['height_status']='Unverified visualization estimate: OSM levels × 3.4 m, or 10.2 m default; range 6–30 m. Not measured height.'
            elif geom.geom_type=='LineString':
                coords=f['geometry']['coordinates']; visual=[]
                # Densify display only in XY along exact linear segments, to follow terrain.
                for p,q in zip(coords,coords[1:]):
                    steps=max(1,math.ceil(math.dist(p[:2],q[:2])/2))
                    for i in range(steps):
                        x=p[0]+(q[0]-p[0])*i/steps; y=p[1]+(q[1]-p[1])*i/steps
                        visual.append([x-origin[0],y-origin[1],sample(x,y)+0.35])
                x,y=coords[-1][:2]; visual.append([x-origin[0],y-origin[1],sample(x,y)+0.35])
                d['display_polyline']=visual
                d['surface_display']=not (t.get('indoor') in ('yes','corridor','room') or t.get('tunnel') not in (None,'no') or t.get('layer') not in (None,'0') or t.get('level') not in (None,'0'))
                d['display_note']='Illustrative DEM-following surface line, not a source elevation or accessible route. Ambiguous/nonzero level and tunnel lines omitted from overview only.'
            elif geom.geom_type=='Point':
                d['ground_center']=sample(geom.x,geom.y)
            else: raise ValueError(f'Unsupported styling geometry {geom.geom_type}')
    result={'run':a.run,'origin_projected_m':origin,'crs':'EPSG:26918','source_z_status':'OSM source Z unknown; source mesh uses zero as explicit placeholder, never inferred from level.',
      'features':[features[k] for k in sorted(features)],'terrain':{'vertices':grid,'nx':len(xs),'ny':len(ys),'sample_spacing_m':4,
      'source':terrain['source'],'source_sha256':terrain['sha256'],'vertical_datum':'NAVD88','description':'4 m presentation grid sampled at native DEM pixel locations; low-poly approximation, not routing terrain.'},
      'validation':validation,'pilot_manifest_sha256':sha(ROOT/'gis/cleaned/pilot/manifest.json'),
      'source_graph_sha256':sha(ROOT/'gis/cleaned/pilot/osm/source_graph.json'),
      'source_graph_path':'gis/cleaned/pilot/osm/source_graph.json','datum_operation_path':'gis/cleaned/pilot/datum_operations.json',
      'protected_scripts':{n:sha(ROOT/n) for n in ['scripts/import_gis.py','scripts/validate_scene.py']}}
    with out.open('xb') as f:f.write(encoded(result))
    print(json.dumps({'path':str(out),'features':len(features),'terrain_vertices':len(grid),'origin':origin,'extent':[xmin,ymin,xmax,ymax]}))

if __name__=='__main__':main()
