"""Read-only source inspection; emits JSON to stdout, never writes GIS geometry.

Geometry transformations below are in-memory measurements only. No snapping,
repair, clipping, simplification, or accessibility inference is performed.
"""
import json
import math
from collections import Counter, defaultdict
import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.warp import transform_bounds
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import transform
from acquire_public_gis import RAW, ROOT

def inspect():
    area=json.loads((ROOT/'gis/pilot_area.json').read_text())
    bounds=area['bbox_wgs84']; region=box(*bounds)
    osm=json.loads((RAW/'osm/pilot.json').read_text())
    elements=osm['elements']; index={(e['type'],e['id']):e for e in elements}
    nodes={e['id']:e for e in elements if e['type']=='node'}
    issues=[]; geometries={}; refs=[]
    for e in elements:
        key=(e['type'],e['id'])
        if e['type']=='node':
            if not all(math.isfinite(e[k]) for k in ['lon','lat']): issues.append(['nonfinite',key])
            geometries[key]=Point(e['lon'],e['lat'])
        elif e['type']=='way':
            missing=[i for i in e['nodes'] if i not in nodes]
            if missing: refs.append([key,missing]); continue
            pts=[(nodes[i]['lon'],nodes[i]['lat']) for i in e['nodes']]
            if len(pts)<2: issues.append(['short_way',key]); continue
            tags=e.get('tags',{})
            is_area = e['nodes'][0]==e['nodes'][-1] and len(pts)>=4 and (tags.get('area')=='yes' or 'building' in tags or 'landuse' in tags or tags.get('natural') in ['wood','water','scrub','grassland']) and tags.get('area')!='no'
            geometries[key]=Polygon(pts) if is_area else LineString(pts)
            if not geometries[key].is_valid: issues.append(['invalid_way_geometry',key])
        else:
            missing=[(m['type'],m['ref']) for m in e['members'] if (m['type'],m['ref']) not in index]
            if missing: refs.append([key,missing])
    scoped=[e for e in elements if (e['type'],e['id']) in geometries and geometries[(e['type'],e['id'])].intersects(region)]
    def counts(items):
        t=[e.get('tags',{}) for e in items]
        roads={'motorway','trunk','primary','secondary','tertiary','unclassified','residential','service','living_street','road','motorway_link','trunk_link','primary_link','secondary_link','tertiary_link'}
        return {'buildings_tagged':sum('building' in a and a['building']!='no' for a in t),
                'path_footway_pedestrian_ways':sum(e['type']=='way' and e.get('tags',{}).get('highway') in {'path','footway','pedestrian'} for e in items),
                'steps_ways':sum(e['type']=='way' and e.get('tags',{}).get('highway')=='steps' for e in items),
                'road_ways':sum(e['type']=='way' and e.get('tags',{}).get('highway') in roads for e in items),
                'entrances_tagged':sum('entrance' in a for a in t),
                'landcover_landuse_tagged':sum('landuse' in a or 'landcover' in a or a.get('natural') in {'wood','scrub','grassland','water'} for a in t)}
    access=defaultdict(Counter)
    for e in scoped:
        for k,v in e.get('tags',{}).items():
            if k.startswith(('wheelchair','ramp','kerb','incline','sidewalk','tactile_paving','handrail','step_count','width','surface','smoothness','access','foot','entrance','level','conveying')):
                access[k][v]+=1
    forward=Transformer.from_crs(4326,26918,always_xy=True)
    ny=json.loads((RAW/'nys/pilot_buildings.json').read_text())
    if ny.get('exceededTransferLimit'): raise RuntimeError('NYS response truncated')
    ny_polys=[]
    for f in ny['features']:
        # ArcGIS exterior rings clockwise, interiors counterclockwise. Associate holes by containment.
        rings=[Polygon([(p[0],p[1]) for p in ring]) for ring in f['geometry']['rings']]
        shells=[p for p in rings if not p.exterior.is_ccw]
        holes=[p for p in rings if p.exterior.is_ccw]
        for shell in shells:
            p=Polygon(shell.exterior.coords,[h.exterior.coords for h in holes if shell.contains(h.representative_point())])
            ny_polys.append((f['attributes'],p))
            if not p.is_valid: issues.append(['invalid_nys_polygon',f['attributes']['OBJECTID']])
    comparisons=[]
    for b in area['buildings']:
        key=(b['osm_type'],b['osm_id']); e=index[key]; p=geometries[key]; projected=transform(forward.transform,p)
        candidates=[(attrs,q) for attrs,q in ny_polys if q.is_valid and projected.is_valid and q.intersects(projected)]
        matches=[{'OBJECTID':a['OBJECTID'],'source_date':a['SOURCEDATE'],
                  'intersection_over_union':projected.intersection(q).area/projected.union(q).area,
                  'osm_area_covered_fraction':projected.intersection(q).area/projected.area} for a,q in candidates]
        comparisons.append({**b,'closed':e['nodes'][0]==e['nodes'][-1],'valid':p.is_valid,
                            'fully_in_pilot':region.covers(p),'area_m2':projected.area,'vertex_count':len(e['nodes'])-1,
                            'osm_edit_timestamp':e.get('timestamp'),'nys_matches':sorted(matches,key=lambda m:-m['intersection_over_union'])})
    rasters=[]
    for file in sorted((RAW/'elevation').glob('*.tif')):
        with rasterio.open(file) as ds:
            envelope=transform_bounds(4326,ds.crs,*bounds,densify_pts=21)
            win=from_bounds(*envelope,ds.transform)
            win=Window(math.floor(win.col_off),math.floor(win.row_off),math.ceil(win.col_off+win.width)-math.floor(win.col_off),math.ceil(win.row_off+win.height)-math.floor(win.row_off))
            a=ds.read(1,window=win,masked=True)
            rr,cc=np.indices(a.shape)
            xx,yy=rasterio.transform.xy(ds.window_transform(win),rr,cc)
            inverse=Transformer.from_crs(ds.crs,4326,always_xy=True)
            lon,lat=inverse.transform(np.asarray(xx).reshape(a.shape),np.asarray(yy).reshape(a.shape))
            inside=(lon>=bounds[0])&(lon<=bounds[2])&(lat>=bounds[1])&(lat<=bounds[3])
            valid=inside&(~np.ma.getmaskarray(a))&np.isfinite(a.data)
            vals=a.data[valid]
            rasters.append({'file':file.relative_to(RAW).as_posix(),'dimensions':[ds.width,ds.height],
                'crs':ds.crs.to_string(),'wkt':ds.crs.to_wkt(),'pixel_size':list(ds.res),'native_bounds':list(ds.bounds),
                'wgs84_bounds':list(transform_bounds(ds.crs,4326,*ds.bounds)), 'nodata':ds.nodata,
                'dtype':ds.dtypes[0],'pilot_pixel_center_count':int(inside.sum()),'valid_pilot_pixel_count':int(valid.sum()),
                'valid_pilot_fraction':float(valid.sum()/inside.sum()),'pilot_min_m':float(vals.min()) if len(vals) else None,
                'pilot_max_m':float(vals.max()) if len(vals) else None,
                'statistics_method':'Native pixel centers inside WGS84 pilot envelope; read-only window; exclude masked/nonfinite values; no resampling.'})
    xy=[(e['lon'],e['lat']) for e in nodes.values()]
    crs=CRS.from_epsg(26918)
    return {'pilot':area,'osm':{'crs':'EPSG:4326 (WGS84 degrees, named lon/lat)',
        'requested_snapshot_utc':area['osm_snapshot_utc'], 'response_server_base':osm['osm3s'],'element_counts':dict(Counter(e['type'] for e in elements)),
        'geometry_counts_all_nonrelations':dict(Counter(g.geom_type for g in geometries.values())),
        'geometry_counts_intersecting_pilot_nonrelations':dict(Counter(geometries[(e['type'],e['id'])].geom_type for e in scoped)),
        'geometry_policy':'Only tagged closed area ways classified as polygons; relations remain raw member graphs, not flattened or merged.',
        'all_response_bounds':[min(x for x,y in xy),min(y for x,y in xy),max(x for x,y in xy),max(y for x,y in xy)],
        'all_response_counts':counts(elements),'pilot_intersecting_nonrelation_counts':counts(scoped),
        'relations':[{'id':e['id'],'tags':e.get('tags',{}),'members':len(e['members'])} for e in elements if e['type']=='relation'],
        'accessibility_related_tag_values':{k:dict(v) for k,v in sorted(access.items())},
        'missing_references':refs,'duplicate_type_ids':len(elements)-len(index),
        'limitations':'Recursive relation members extend beyond pilot. Counts of ways are source segments, not physical path counts. Missing accessibility tags mean unknown; tags are unverified claims.'},
        'nys':{'count':len(ny['features']),'crs':ny['spatialReference'],'geometry_type':ny['geometryType'],
               'source_dates':dict(Counter(f['attributes']['SOURCEDATE'] for f in ny['features'])),
               'sources':dict(Counter(f['attributes']['NYSGEO_SOURCE'] for f in ny['features'])),
               'fields':[f['name'] for f in ny['fields']],
               'native_bounds':[min(p.bounds[0] for a,p in ny_polys),min(p.bounds[1] for a,p in ny_polys),max(p.bounds[2] for a,p in ny_polys),max(p.bounds[3] for a,p in ny_polys)],
               'comparison_note':'Intersection measurements only, in memory; no source merge or repair. Overlap is not a survey accuracy measurement. Z retained in raw response but not interpreted as reliable height.'},
        'selected_building_comparison':comparisons,'elevation':rasters,'issues':issues,
        'recommended_crs':{'epsg':26918,'name':crs.name,'area_of_use':str(crs.area_of_use),'units':crs.axis_info[0].unit_name,
            'rationale':'Pilot is within UTM zone 18N; meter coordinates align with NYS service and standard USGS DEM headers. Native inputs untouched.',
            'datum_caution':'OSM WGS84 and NAD83 realizations are not survey-equivalent. USGS project metadata may specify NAD83(2011) while standard raster says NAD83. Future processing must record actual PROJ operation, accuracy, grids and vertical datum separately; no invented datum precision.',
            'local_origin':None,'vertical_reference':'NAVD88 meters per USGS metadata; not an ellipsoidal height.'}}

if __name__=='__main__':
    print(json.dumps(inspect(),indent=2))
