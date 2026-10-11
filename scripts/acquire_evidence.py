"""Append-only acquisition for the imagery/elevation evidence review.

Never writes gis/raw or any existing source/scene. Sealing closes this snapshot.
Use: python scripts/acquire_evidence.py fetch URL RELATIVE_PATH [JSON_PARAMETERS]
"""
import json
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import acquire_public_gis as acquisition

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=ROOT/'gis/acquisitions/evidence_20261010_01'
acquisition.RAW=SNAPSHOT/'source'

def fetch(url,name,params=None):
    dest=acquisition.RAW/name
    if not dest.resolve().is_relative_to(acquisition.RAW.resolve()):raise ValueError(name)
    if (acquisition.RAW.parent/'SHA256SUMS.txt').exists():raise RuntimeError('Snapshot sealed')
    if dest.exists() or dest.with_suffix(dest.suffix+'.http.json').exists():raise FileExistsError(dest)
    started=datetime.now(timezone.utc).isoformat()
    response=acquisition.SESSION.get(url,params=params,timeout=(30,120))
    response.raise_for_status()
    if 'json' in response.headers.get('Content-Type',''):
        value=response.json()
        if isinstance(value,dict) and (value.get('error') or value.get('errors')):raise RuntimeError(value)
    acquisition.write_new(dest,response.content)
    meta={'requested_url':url,'resolved_url':response.url,'parameters':params,'method':'GET',
          'download_started_utc':started,'download_completed_utc':datetime.now(timezone.utc).isoformat(),
          'response_headers':dict(response.headers),'bytes':len(response.content),
          'sha256':hashlib.sha256(response.content).hexdigest()}
    acquisition.write_new(dest.with_suffix(dest.suffix+'.http.json'),json.dumps(meta,sort_keys=True,indent=2))
    print(json.dumps({'file':str(dest),'bytes':len(response.content),'sha256':meta['sha256']}),flush=True)
    return response.content

if __name__=='__main__':
    action=sys.argv[1]
    if action=='fetch':
        fetch(sys.argv[2],sys.argv[3],json.loads(sys.argv[4]) if len(sys.argv)>4 else None)
    elif action=='catalog':
        requests=[
          ('https://orthos.its.ny.gov/arcgis/rest/services/wms/2024/MapServer','ortho/service_2024.json',{'f':'pjson'}),
          ('https://orthos.its.ny.gov/arcgis/rest/services/wms/2024/MapServer/info/iteminfo','ortho/iteminfo_2024.json',{'f':'pjson'}),
          ('https://orthos.its.ny.gov/arcgis/rest/services','ortho/service_directory.json',{'f':'pjson'}),
          ('https://gis.ny.gov/orthoimagery','policy/orthoimagery.html',None),
          ('https://gis.ny.gov/orthoimagery-faqs','policy/orthoimagery_faq.html',None),
          ('https://gis.ny.gov/lidar','policy/lidar.html',None),
          ('https://gis.ny.gov/2024-orthoimagery','policy/ortho_2024.html',None),
          ('https://tnmaccess.nationalmap.gov/api/v1/datasets','elevation/tnm_datasets.json',None),
        ]
        for url,name,params in requests:
            if (acquisition.RAW/name).exists():continue
            fetch(url,name,params)
    elif action=='search':
        bbox=json.loads((ROOT/'gis/pilot_area.json').read_text())['bbox_wgs84']
        for label,dataset in [('dem','Digital Elevation Model (DEM) 1 meter'),('lpc','Lidar Point Cloud (LPC)')]:
            fetch('https://tnmaccess.nationalmap.gov/api/v1/products',f'elevation/products_{label}.json',
                  {'bbox':','.join(map(str,bbox)),'datasets':dataset,'max':100,'outputFormat':'JSON'})
        fetch('https://orthos.its.ny.gov/arcgis/rest/services/vector','ortho/vector_services.json',{'f':'pjson'})
        fetch('https://orthos.its.ny.gov/arcgis/rest/services/Dynamic','ortho/dynamic_services.json',{'f':'pjson'})
    elif action=='coverage':
        bbox=json.loads((ROOT/'gis/pilot_area.json').read_text())['bbox_wgs84']
        params={'f':'json','where':'1=1','geometry':','.join(map(str,bbox)),
          'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects',
          'outFields':'*','returnGeometry':'true','resultRecordCount':1000}
        for group,service,ids in [('ortho','ortho_indexes',range(10)),('elevation','las_indexes',range(7))]:
            for layer in ids:
                name=f'{group}/coverage_{layer:02d}.json'
                if (acquisition.RAW/name).exists():continue
                value=json.loads(fetch(f'https://orthos.its.ny.gov/arcgis/rest/services/vector/{service}/MapServer/{layer}/query',name,params))
                if value.get('exceededTransferLimit'):raise RuntimeError('Truncated coverage query')
        for suffix in ('4_2018','1_2020'):
            project='NY_FEMAR2_Central_2018_D19/NY_FEMAR2_Central_'+suffix if suffix=='4_2018' else 'NY_HudsonRiverRegion_2020_A20/NY_HudsonRiverRegion_'+suffix
            fetch('https://prd-tnm.s3.amazonaws.com/',f'elevation/metadata_listing_{suffix}.xml',
                  {'prefix':'StagedProducts/Elevation/metadata/'+project+'/'})
    elif action=='imagery-tiles':
        entries=json.loads((acquisition.RAW/'ortho/coverage_08.json').read_text())['features']
        for feature in sorted(entries,key=lambda f:f['attributes']['FILENAME']):
            url=feature['attributes']['DIRECT_DL']
            name='ortho/'+url.rsplit('/',1)[1]
            if not (acquisition.RAW/name).exists():fetch(url,name)
    elif action=='comparison-inputs':
        grids=['us_noaa_nadcon5_nad83_1986_nad83_harn_conus.tif',
               'us_noaa_nadcon5_nad83_2007_nad83_2011_conus.tif',
               'us_noaa_nadcon5_nad83_fbn_nad83_2007_conus.tif',
               'us_noaa_nadcon5_nad83_harn_nad83_fbn_conus.tif']
        for grid in grids:
            if not (acquisition.RAW/'datum'/grid).exists():fetch('https://cdn.proj.org/'+grid,'datum/'+grid)
        catalog=json.loads((acquisition.RAW/'elevation/products_lpc.json').read_text())
        for item in catalog['items']:
            if 'NY_FEMAR2_Central_2018_D19' not in item['title']:continue
            url=item['downloadURL'];name='elevation/'+url.rsplit('/',1)[1]
            if not (acquisition.RAW/name).exists():fetch(url,name)
    else:raise ValueError(action)
