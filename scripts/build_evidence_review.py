"""Read-only imagery/LiDAR comparison; no geographic corrections or scene edits.

All new outputs use an exclusive-create review directory. Native imagery remains
in its original ZIP, read through GDAL. Local datum grids are enabled only inside
this process and never change the original pilot pipeline's datum operation.
"""
import argparse
import hashlib
import json
import math
import zipfile
import os
from pathlib import Path
from collections import Counter
import numpy as np
import pyproj
from pyproj import CRS, Transformer, datadir, network
from pyproj.transformer import TransformerGroup
import rasterio
from rasterio.merge import merge
from shapely.geometry import shape, Polygon, box, mapping
from shapely.ops import transform, unary_union
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[1] / '.local/mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import laspy

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'gis/acquisitions/evidence_20261010_01/source'
PILOT=ROOT/'gis/cleaned/pilot'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

def setup_transform(src,dst):
    group=TransformerGroup(src,dst,always_xy=True,allow_ballpark=False)
    if not group.best_available or not group.transformers:raise RuntimeError('Required datum grids unavailable')
    return group.transformers[0]

def operation(t):
    return {'description':t.description,'accuracy_m':t.accuracy,'pipeline':t.definition,
            'projjson':t.to_json_dict()}

def load_features():
    result={}
    for layer in ['buildings','paths','roads','stairs']:
        for f in read(PILOT/'osm'/f'{layer}.json')['features']:
            if f['id'] not in result:result[f['id']]={'feature':f,'layers':[]}
            result[f['id']]['layers'].append(layer)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'gis/cleaned/evidence_20261010_01')
    args=parser.parse_args();out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    network.set_network_enabled(False)
    # Immutable grids, explicit process-local search path; no silent downloads.
    datadir.append_data_dir(str(SOURCE/'datum'))
    forward=setup_transform(26918,6537);inverse=setup_transform(6537,26918)
    features=load_features()
    buildings=[d['feature'] for k,d in sorted(features.items()) if 'buildings' in d['layers']]
    selected=read(ROOT/'gis/pilot_area.json')
    # Use the existing pilot's own projected envelope as the evidence AOI.
    target_ids={'osm/'+f['osm_type']+'/'+str(f['osm_id']) for f in selected['buildings']}
    target_union=unary_union([shape(f['geometry']) for f in buildings if f['id'] in target_ids])
    study=box(target_union.bounds[0]-50,target_union.bounds[1]-50,target_union.bounds[2]+50,target_union.bounds[3]+50)
    native_study=transform(forward.transform,study)
    tile_records=[];datasets=[]
    for path in sorted((SOURCE/'ortho').glob('*.zip')):
        with zipfile.ZipFile(path) as archive:
            name=next(n for n in archive.namelist() if n.endswith('.jp2'))
            members={n:hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()}
        ds=rasterio.open('/vsizip/'+path.resolve().as_posix()+'/'+name);datasets.append(ds)
        if CRS(ds.crs)!=CRS.from_epsg(6537):raise RuntimeError('Unexpected native imagery CRS')
        tile_records.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'member_sha256':members,
            'crs_wkt':ds.crs.to_wkt(),'epsg':6537,'units':'US survey foot','unit_to_m':1200/3937,
            'bounds':list(ds.bounds),'pixel_size_native':list(ds.res),'shape':[ds.height,ds.width],
            'bands':ds.count,'colorinterp':[x.name for x in ds.colorinterp],
            'acquisition_period':'Spring 2024, service-level statement; exact campus flight day unresolved',
            'license_status':'NYS as-is terms and attribution; no standardized redistribution license asserted'})
    mosaic,affine=merge(datasets,indexes=[1,2,3])
    for ds in datasets:ds.close()
    left,top=affine*(0,0);right,bottom=affine*(mosaic.shape[2],mosaic.shape[1])
    extent=[left,right,bottom,top]
    image=np.moveaxis(mosaic,0,2)
    transformed={key:transform(forward.transform,shape(d['feature']['geometry'])) for key,d in features.items()}
    max_roundtrip=0
    for f in buildings:
        coords=np.array(f['geometry']['coordinates'][0]);x,y=forward.transform(coords[:,0],coords[:,1]);xx,yy=inverse.transform(x,y)
        max_roundtrip=max(max_roundtrip,float(np.max(np.abs(np.column_stack([xx,yy])-coords[:,:2]))))
    grid_records={p.name:sha(p) for p in sorted((SOURCE/'datum').glob('*.tif'))}
    write(out/'imagery_review.json',{'tiles':tile_records,'selected_year':2024,'native_resolution_m':1200/3937,
       '2025_index_hits':sum(len(read(SOURCE/'ortho'/f'coverage_{i:02d}.json')['features']) for i in range(5)),
       'native_aoi_bounds':list(native_study.bounds),'comparison_aoi_26918':mapping(study),
       'aoi_note':'50 m rectangular margin around the same seven target footprints; imagery only, no feature clipping',
       'datum_operation':operation(forward),'inverse_operation':operation(inverse),'grid_sha256':grid_records,
       'max_coordinate_roundtrip_error_m':max_roundtrip,'inherited_source_datum_accuracy_m':4,
       'limitations':['0.2 m transformation accuracy is not imagery or OSM positional accuracy.',
                      'Tall building roof displacement, shadows, tree cover and capture date differences limit visual conclusions.',
                      'Native 1 ft pixels do not establish survey accuracy or accessibility.']})
    write(out/'building_index.json',[{'index':i+1,'source_id':f['id'],'name':f['source'].get('tags',{}).get('name'),'geometry':f['geometry']} for i,f in enumerate(buildings)])

    def draw(ax,bounds,overlay=True,labels=True):
        ax.imshow(image,extent=extent,origin='upper')
        if overlay:
            for key,d in sorted(features.items()):
                geom=transformed[key];tags=d['feature']['source'].get('tags',{})
                if geom.geom_type=='LineString':
                    # Same explicit surface display predicate as the validated pilot.
                    surface=not(tags.get('indoor') in ('yes','corridor','room') or tags.get('tunnel') not in (None,'no') or tags.get('layer') not in (None,'0') or tags.get('level') not in (None,'0'))
                    if not surface:continue
                    color='#ff725c' if 'roads' in d['layers'] else '#ffe64c' if 'stairs' not in d['layers'] else '#f178fa'
                    xs,ys=geom.xy;ax.plot(xs,ys,color=color,lw=.7,alpha=.9)
                elif geom.geom_type=='Polygon':
                    xs,ys=geom.exterior.xy;ax.plot(xs,ys,color='#00ecff',lw=1.0)
            if labels:
                for i,f in enumerate(buildings):
                    geom=transformed[f['id']];pt=geom.representative_point()
                    if bounds[0]<pt.x<bounds[2] and bounds[1]<pt.y<bounds[3]:
                        ax.text(pt.x,pt.y,str(i+1),color='white',fontsize=8,ha='center',va='center',bbox={'facecolor':'black','alpha':.7,'pad':1,'edgecolor':'none'})
        ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[1],bounds[3]);ax.set_aspect('equal');ax.ticklabel_format(style='plain',useOffset=False)
        ax.set_xlabel('NAD83(2011) / NY East — US survey feet');ax.set_ylabel('Northing (ftUS)')
    bounds=native_study.bounds
    for label,overlay in [('imagery_overview',False),('source_overlay',True)]:
        fig,ax=plt.subplots(figsize=(16,8));draw(ax,bounds,overlay)
        ax.set_title('RPI pilot / NYS Spring 2024 imagery'+(' + unchanged source geometry' if overlay else ''))
        fig.text(.5,.015,'NYS ITS Geospatial Services | OSM contributors | cyan: footprints; yellow: paths; coral: roads; magenta: stairs | review only',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.035,1,1));fig.savefig(out/f'{label}.png',dpi=170);plt.close(fig)
    # Six numbered targets with both imagery-only and overlay panels for visual QA.
    inspect_ids=['osm/way/104737293','osm/way/104737317','osm/way/104737313','osm/way/104737275','osm/way/104737234','osm/way/104737202']
    for key in inspect_ids:
        g=transformed[key];b=g.buffer(70).bounds;fig,axs=plt.subplots(1,2,figsize=(15,8))
        for ax,overlay in zip(axs,[False,True]):draw(ax,b,overlay);ax.set_title('Source overlay' if overlay else '2024 imagery')
        fig.suptitle(features[key]['feature']['source']['tags']['name']+' / '+key)
        fig.text(.5,.01,'NYS ITS Geospatial Services / OSM contributors — roof edges are not necessarily ground-level footprints',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.035,1,.96));fig.savefig(out/(key.replace('/','_')+'_review.png'),dpi=150);plt.close(fig)
    write(out/'source_hashes.json',{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()})
    print(json.dumps({'output':str(out),'imagery_tiles':len(tile_records),'transform_accuracy_m':forward.accuracy,'roundtrip_m':max_roundtrip}),flush=True)

if __name__=='__main__':main()
