# RPI public GIS acquisition — 2026-10-10

Raw acquisition is sealed. Do not overwrite any file here. Exact requests, UTC download timestamps, HTTP headers, file hashes and source-specific limitations are in `sources.json` and adjacent `*.http.json` files.

## Pilot and source choice

WGS84 west/south/east/north: **-73.683585, 42.728278, -73.675583, 42.730755**. Approximately 655 × 275 m. Derived from seven named OSM footprints plus a 50 m geodesic envelope margin; no clipping performed.

OSM: © OpenStreetMap contributors, ODbL 1.0; https://www.openstreetmap.org/copyright . Complete source IDs, versions, timestamps, tags and graph references retained. Pilot query date 2026-10-10T04:03:46Z; response server-base time is a separate field, not the historical query time.

USGS: public domain, credit USGS. Selected FEMA Central 1 m tile has 100% pilot coverage, NAVD88 elevations 48.973–82.301 m. Both standard tiles are 10012 × 10012 pixels, EPSG:26918, 1 m, NoData -999999. Hudson D22 has only 2.772% valid pilot coverage and is rejected. One standard ~10 km tile per candidate was acquired, not an entire regional collection; FEMA is 334.7 MB and Hudson 76.3 MB.

FEMA product published 2024-01-04; tile metadata temporal extent 2019-01-04 to 2020-09-25. API-linked Block 1 vendor XML describes other counties; its acquisition dates/geoid/accuracy are not assigned to RPI. Exact local collection date and achieved vertical accuracy remain unknown. Hudson project metadata gives 2022-11-08 to 2023-04-15 but leaves measured accuracy blank.

NYS: 27 original full footprints in native EPSG:26918, all NYSERDA from 2014 NYS orthoimagery. Useful fields: source organization, source imagery/tile ID, source year, county, municipality, OBJECTID. All seven targets overlap a NYS polygon but differences remain unresolved. Keep as a separate comparison layer. State as-is terms and attribution are saved in `nys/iteminfo.json`; do not label it CC0 or assume a standardized redistribution license.

Working CRS recommendation: EPSG:26918 (NAD83 / UTM zone 18N), meters. Raw inputs remain native. No local Blender origin established. Future conversion must record actual datum operations and their accuracy; NAVD88 elevations must remain distinct from ellipsoidal heights.

NYS elevation catalog https://gis.ny.gov/lidar was inspected; redundant statewide lidar/imagery/roads were not downloaded. USGS supplied sufficient 1 m coverage. No Google assets used. Approximate path JSON excluded.

## Exact downloaded response files

| File relative to gis/raw | Bytes | Provider | Source URL |
| --- | ---: | --- | --- |
| `elevation/DEM_Dewberry.xml` | 8679 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/metadata/NY_FEMAR2_Central_2018_D19/NY_FEMAR2_Central_B1_2018/reports/vendor_provided_xml/DEM_Dewberry.xml |
| `elevation/fema_metadata_listing.xml` | 6117 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://prd-tnm.s3.amazonaws.com/?list-type=2&prefix=StagedProducts/Elevation/metadata/NY_FEMAR2_Central_2018_D19/NY_FEMAR2_Central_B1_2018/reports/ |
| `elevation/fema_product_listing.xml` | 407347 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://prd-tnm.s3.amazonaws.com/?list-type=2&prefix=StagedProducts/Elevation/1m/Projects/NY_FEMAR2_Central_2018_D19/ |
| `elevation/fema_sciencebase_item.json` | 12242 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://www.sciencebase.gov/catalog/item/65af5662d34ef34c3506da11?format=json |
| `elevation/fema_xml_listing.xml` | 306 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://prd-tnm.s3.amazonaws.com/?list-type=2&prefix=StagedProducts/Elevation/1m/Projects/NY_FEMAR2_Central_2018_D19/XML/ |
| `elevation/hudson_metadata_listing.xml` | 334378 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://prd-tnm.s3.amazonaws.com/?list-type=2&prefix=StagedProducts/Elevation/metadata/NY_Hudson_D22/NY_Hudson_1_D22 |
| `elevation/NY_Hudson_1_D22_ClassifiedPointCloud.xml` | 16159 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://gisdata.ny.gov/elevation/LIDAR/USGS_LakeOntarioHudsonRiverRegion2022/NY_Hudson_1_D22_ClassifiedPointCloud.xml |
| `elevation/NY_Hudson_1_D22_DigitalElevationModel.xml` | 8567 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/metadata/NY_Hudson_D22/NY_Hudson_1_D22/reports/vendor_provided_xml/NY_Hudson_1_D22_DigitalElevationModel.xml |
| `elevation/products_1m.json` | 8174 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://tnmaccess.nationalmap.gov/api/v1/products?bbox=-73.683585%2C42.728278%2C-73.675583%2C42.730755&datasets=Digital+Elevation+Model+%28DEM%29+1+meter&max=100&outputFormat=JSON |
| `elevation/products_opr.json` | 745 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://tnmaccess.nationalmap.gov/api/v1/products?bbox=-73.683585%2C42.728278%2C-73.675583%2C42.730755&datasets=Digital+Elevation+Model+%28DEM%29+-+Original+Product+Resolution&max=100&outputFormat=JSON |
| `elevation/USGS_1M_18_x60y474_NY_FEMAR2_Central_2018_D19.tif` | 334705804 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/NY_FEMAR2_Central_2018_D19/TIFF/USGS_1M_18_x60y474_NY_FEMAR2_Central_2018_D19.tif |
| `elevation/USGS_1M_18_x60y474_NY_FEMAR2_Central_2018_D19.xml` | 13958 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://thor-f5.er.usgs.gov/ngtoc/metadata/waf/elevation/1_meter/geotiff/NY_FEMAR2_Central_2018_D19/USGS_1M_18_x60y474_NY_FEMAR2_Central_2018_D19.xml |
| `elevation/USGS_1M_18_x60y474_NY_Hudson_D22.tif` | 76320460 | USGS 3DEP / The National Map (NYS hosts one USGS project metadata copy) | https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/NY_Hudson_D22/TIFF/USGS_1M_18_x60y474_NY_Hudson_D22.tif |
| `nys/county_layer.json` | 8411 | NYS ITS Geospatial Services; NYSERDA/CIESIN for all 27 acquired footprints | https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer/1?f=pjson |
| `nys/iteminfo.json` | 5058 | NYS ITS Geospatial Services; NYSERDA/CIESIN for all 27 acquired footprints | https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer/info/iteminfo?f=pjson |
| `nys/layer.json` | 5223 | NYS ITS Geospatial Services; NYSERDA/CIESIN for all 27 acquired footprints | https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer/2?f=pjson |
| `nys/pilot_buildings.json` | 20802 | NYS ITS Geospatial Services; NYSERDA/CIESIN for all 27 acquired footprints | https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer/2/query?f=json&where=1%3D1&geometry=-73.683585%2C42.728278%2C-73.675583%2C42.730755&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=%2A&returnGeometry=true&returnZ=true&orderByFields=OBJECTID&resultRecordCount=50000 |
| `nys/rensselaer_county.json` | 1142 | NYS ITS Geospatial Services; NYSERDA/CIESIN for all 27 acquired footprints | https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer/1/query?f=json&where=NAME%3D%27Rensselaer%27&outFields=*&returnGeometry=false |
| `nys/service.json` | 7828 | NYS ITS Geospatial Services; NYSERDA/CIESIN for all 27 acquired footprints | https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer?f=pjson |
| `osm/discovery.json` | 1557765 | OpenStreetMap contributors via Overpass API | https://overpass-api.de/api/interpreter |
| `osm/pilot.json` | 1120670 | OpenStreetMap contributors via Overpass API | https://overpass-api.de/api/interpreter |

Each downloaded file has a corresponding `.http.json` provenance sidecar. OSM query files are `osm/discovery.overpassql` and `osm/pilot.overpassql`. `sources.json`, this document, and `SHA256SUMS.txt` are locally generated acquisition records.

## Checks and limitations

No duplicate OSM type/ID pairs or missing way-node/relation-member references. Seven target footprints closed, valid, and fully in pilot. NYS response not truncated. Inventory polygon checks passed; relation geometries have NOT been assembled or validated as polygons. This is acquisition integrity, not a passing routing/import validator.

Pilot-intersecting nonrelation counts: 27 tagged building ways; 243 path/footway/pedestrian ways; 52 steps ways; 53 road ways; 45 entrance-tagged elements. There is also one raw building multipolygon relation; do not sum representations blindly. Indoor/multilevel paths are included. Full recursive response: 3363 nodes, 741 ways, 4 relations. Dependencies include bus routes outside pilot.

Accessibility-related tags exist (wheelchair, ramp, kerb, incline, handrail, step_count, tactile_paving, width, surface, level, access). They are unverified source claims, not proof of accessibility. Missing values remain unknown. Source crossings must not be merged by XY proximity.

Next: verify SHA-256, review unresolved footprint differences and vertical metadata, then implement deterministic source-preserving layer conversion and validation under gis/cleaned. No Blender processing in this acquisition phase.
