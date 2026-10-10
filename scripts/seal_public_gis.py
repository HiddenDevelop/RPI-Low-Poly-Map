"""One-time inventory, provenance manifest and integrity seal for this acquisition.

Refuses existing outputs. Downloaded files are only read. Acquisition records
are checked against hashes taken immediately after each HTTP download.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from acquire_public_gis import RAW, ROOT, write_new
from inspect_public_gis import inspect

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    targets=[RAW/'SOURCES.md',RAW/'sources.json',RAW/'SHA256SUMS.txt',ROOT/'gis/inventory_2026-10-10.json']
    for p in targets:
        if p.exists(): raise FileExistsError(p)
    inventory=inspect()
    if inventory['osm']['missing_references'] or inventory['osm']['duplicate_type_ids'] or inventory['issues']:
        raise RuntimeError('Inventory contains integrity/geometry issues; review before sealing')
    records=[]
    for sidecar in sorted(RAW.rglob('*.http.json')):
        meta=json.loads(sidecar.read_text())
        source=Path(str(sidecar)[:-len('.http.json')])
        if digest(source)!=meta['sha256']: raise RuntimeError(f'Download changed: {source}')
        rel=source.relative_to(RAW).as_posix()
        if rel.startswith('osm/'):
            provider='OpenStreetMap contributors via Overpass API'
            license='Open Database License (ODbL) 1.0; attribution: © OpenStreetMap contributors'
            terms='https://www.openstreetmap.org/copyright'
            crs='EPSG:4326; WGS84 latitude/longitude degrees'
            use='Initial vector source; discovery response locates named buildings; pilot response preserves full node/way/relation references.'
            limits='Volunteer data, not surveyed. Unknown accessibility remains unknown. Relation dependencies extend outside acquisition bounds. Edit timestamps are not survey dates.'
        elif rel.startswith('nys/'):
            provider='NYS ITS Geospatial Services; NYSERDA/CIESIN for all 27 acquired footprints'
            license='State service as-is usage terms; attribution NYSERDA, CIESIN, NYS ITS Geospatial Services. No specific standardized redistribution license asserted.'
            terms='https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer/info/iteminfo?f=pjson'
            crs='EPSG:26918; NAD83 / UTM zone 18N, meters (service and actual response)'
            use='Independent comparison only, not merged or substituted for OSM'
            limits='27 features derived from 2014 NYS orthoimagery; county range 2010–2017. Disagreements unresolved. No accessibility, height, or current-condition guarantee. Service prose says Web Mercator but actual layer/response says 26918; honor actual response.'
        else:
            provider='USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy)'
            license='USGS 3DEP public domain; credit USGS and originating agencies; no accuracy warranty'
            terms='https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits'
            crs='Raster headers: EPSG:26918 meters; vertical NAVD88 meters. Metadata/catalog documents retain their original CRS descriptions.'
            use='Bare-earth terrain reference; FEMA Central selected, Hudson retained as rejected partial-coverage candidate; catalogs/XML document selection.'
            limits='DEM is not a pedestrian surface/accessibility survey. Hudson covers only 2.77% of pilot. FEMA tile temporal extent 2019-01-04 to 2020-09-25; site-specific flight date and measured accuracy unconfirmed. Block-1 vendor metadata names Niagara/Westchester and must not be attributed to RPI.'
        record={**meta,'file':rel,'original_filename':source.name,'provider':provider,'license_terms':license,'terms_url':terms,
                'native_crs':crs,'intended_use':use,'known_limitations':limits,
                'geographic_query_bounds_wgs84':inventory['pilot']['bbox_wgs84'] if rel in ['osm/pilot.json','nys/pilot_buildings.json','elevation/products_1m.json','elevation/products_opr.json'] else None,
                'acquisition_date_utc':meta['download_completed_utc'],'spatial_resolution': '1 meter raster pixels' if source.suffix=='.tif' else 'Not applicable (vector or metadata)'}
        raster=next((r for r in inventory['elevation'] if r['file']==rel),None)
        if raster: record['raster_inventory']=raster
        if rel=='osm/pilot.json': record['actual_response_bounds_wgs84']=inventory['osm']['all_response_bounds']
        if rel=='nys/pilot_buildings.json': record['actual_native_bounds']=inventory['nys']['native_bounds']
        if rel=='osm/discovery.json':
            record['geographic_query_bounds_wgs84']=None
            record['query_area']='1200 m around latitude 42.729014 longitude -73.676728'
        records.append(record)
    result={'schema_version':1,'sealed_at_utc':datetime.now(timezone.utc).isoformat(),
            'downloads':records,'pilot':inventory['pilot'],
            'selected_elevation':'elevation/USGS_1M_18_x60y474_NY_FEMAR2_Central_2018_D19.tif',
            'crs_recommendation':inventory['recommended_crs'],
            'raw_policy':'New files created during acquisition only; all now immutable. Download response bodies preserved without GIS changes. HTTP content decoding may remove transfer compression. No geometry exported/reprojected.',
            'integrity':'SHA256SUMS.txt covers every raw file except itself, including this manifest, request sidecars, queries, and .gitkeep.',
            'metadata_caveat':'Use tile-specific USGS XML temporal extent 20190104–20200925. The API vendorMetaUrl chooses Block 1, which does not establish RPI flight dates or accuracy. Hudson vendor XML has blank measured-accuracy fields.',
            'automation_status':'All requested core datasets acquired automatically; no access restrictions bypassed. Initial NYS county query used wrong field and returned HTTP API error; corrected to NAME using layer schema. EPSG website returned 403 through browser; recommendation uses local PROJ/EPSG database plus source CRS metadata.'}
    write_new(ROOT/'gis/inventory_2026-10-10.json',json.dumps(inventory,indent=2))
    write_new(RAW/'sources.json',json.dumps(result,indent=2,ensure_ascii=False))
    lines=['# RPI public GIS acquisition — 2026-10-10','',
       'Raw acquisition is sealed. Do not overwrite any file here. Exact requests, UTC download timestamps, HTTP headers, file hashes and source-specific limitations are in `sources.json` and adjacent `*.http.json` files.',
       '', '## Pilot and source choice','',
       'WGS84 west/south/east/north: **-73.683585, 42.728278, -73.675583, 42.730755**. Approximately 655 × 275 m. Derived from seven named OSM footprints plus a 50 m geodesic envelope margin; no clipping performed.',
       '', 'OSM: © OpenStreetMap contributors, ODbL 1.0; https://www.openstreetmap.org/copyright . Complete source IDs, versions, timestamps, tags and graph references retained. Pilot query date 2026-10-10T04:03:46Z; response server-base time is a separate field, not the historical query time.',
       '', 'USGS: public domain, credit USGS. Selected FEMA Central 1 m tile has 100% pilot coverage, NAVD88 elevations 48.973–82.301 m. Both standard tiles are 10012 × 10012 pixels, EPSG:26918, 1 m, NoData -999999. Hudson D22 has only 2.772% valid pilot coverage and is rejected. One standard ~10 km tile per candidate was acquired, not an entire regional collection; FEMA is 334.7 MB and Hudson 76.3 MB.',
       '', 'FEMA product published 2024-01-04; tile metadata temporal extent 2019-01-04 to 2020-09-25. API-linked Block 1 vendor XML describes other counties; its acquisition dates/geoid/accuracy are not assigned to RPI. Exact local collection date and achieved vertical accuracy remain unknown. Hudson project metadata gives 2022-11-08 to 2023-04-15 but leaves measured accuracy blank.',
       '', 'NYS: 27 original full footprints in native EPSG:26918, all NYSERDA from 2014 NYS orthoimagery. Useful fields: source organization, source imagery/tile ID, source year, county, municipality, OBJECTID. All seven targets overlap a NYS polygon but differences remain unresolved. Keep as a separate comparison layer. State as-is terms and attribution are saved in `nys/iteminfo.json`; do not label it CC0 or assume a standardized redistribution license.',
       '', 'Working CRS recommendation: EPSG:26918 (NAD83 / UTM zone 18N), meters. Raw inputs remain native. No local Blender origin established. Future conversion must record actual datum operations and their accuracy; NAVD88 elevations must remain distinct from ellipsoidal heights.',
       '', 'NYS elevation catalog https://gis.ny.gov/lidar was inspected; redundant statewide lidar/imagery/roads were not downloaded. USGS supplied sufficient 1 m coverage. No Google assets used. Approximate path JSON excluded.',
       '', '## Exact downloaded response files','', '| File relative to gis/raw | Bytes | Provider | Source URL |','| --- | ---: | --- | --- |']
    for r in records:
        lines.append(f"| `{r['file']}` | {r['bytes']} | {r['provider']} | {r['resolved_url']} |")
    lines += ['', 'Each downloaded file has a corresponding `.http.json` provenance sidecar. OSM query files are `osm/discovery.overpassql` and `osm/pilot.overpassql`. `sources.json`, this document, and `SHA256SUMS.txt` are locally generated acquisition records.',
              '', '## Checks and limitations','',
              'No duplicate OSM type/ID pairs or missing way-node/relation-member references. Seven target footprints closed, valid, and fully in pilot. NYS response not truncated. Inventory polygon checks passed; relation geometries have NOT been assembled or validated as polygons. This is acquisition integrity, not a passing routing/import validator.',
              '', 'Pilot-intersecting nonrelation counts: 27 tagged building ways; 243 path/footway/pedestrian ways; 52 steps ways; 53 road ways; 45 entrance-tagged elements. There is also one raw building multipolygon relation; do not sum representations blindly. Indoor/multilevel paths are included. Full recursive response: 3363 nodes, 741 ways, 4 relations. Dependencies include bus routes outside pilot.',
              '', 'Accessibility-related tags exist (wheelchair, ramp, kerb, incline, handrail, step_count, tactile_paving, width, surface, level, access). They are unverified source claims, not proof of accessibility. Missing values remain unknown. Source crossings must not be merged by XY proximity.',
              '', 'Next: verify SHA-256, review unresolved footprint differences and vertical metadata, then implement deterministic source-preserving layer conversion and validation under gis/cleaned. No Blender processing in this acquisition phase.']
    write_new(RAW/'SOURCES.md','\n'.join(lines)+'\n')
    hashes=[f'{digest(p)}  {p.relative_to(RAW).as_posix()}' for p in sorted(RAW.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt']
    write_new(RAW/'SHA256SUMS.txt','\n'.join(hashes)+'\n')
    print(f'Sealed {len(records)} downloaded responses and {len(hashes)} raw files. Download-time hashes verified.')

if __name__=='__main__': main()
