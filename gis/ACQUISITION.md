# Public-data acquisition and initial inspection

Completed 2026-10-10. No Blender changes, GIS geometry exports, clipping, simplification, repair, source merging, or accessibility classification were performed. The approximate route JSON is excluded.

## Files and reproducibility

- `raw/SOURCES.md`: readable inventory, selection decisions, licenses and exact download URLs.
- `raw/sources.json`: every downloaded response, request parameters, UTC timestamps, original filename, CRS, intended use and limitations.
- `raw/SHA256SUMS.txt`: every raw file except itself, including query files and provenance documents.
- `inventory_2026-10-10.json`: measured geometry, tag, footprint-comparison and raster inventory.
- `pilot_area.json`: data-derived pilot boundary and seven source building IDs.
- `../scripts/acquire_public_gis.py`: exclusive-create HTTP acquisition and integrity verification. Refuses new downloads after sealing.
- `../scripts/define_pilot_area.py`: deterministic footprint-envelope calculation.
- `../scripts/inspect_public_gis.py`: read-only measurements; writes only to stdout.
- `../scripts/seal_public_gis.py`: one-time manifest/inventory writer, refusing existing outputs.
- `../scripts/replay_public_gis.py`: repeats saved requests into a new `gis/acquisitions/NAME/raw/` directory. Existing original raw files remain untouched.
- `../scripts/gis-requirements-lock.txt`: Python dependency versions used. Runtime: Python 3.13, isolated in ignored `.local/gis-venv/`.

Run from the repository root in PowerShell:

```powershell
.local/gis-venv/Scripts/python.exe scripts/acquire_public_gis.py verify
.local/gis-venv/Scripts/python.exe scripts/inspect_public_gis.py
```

To recreate the runtime if needed:

```powershell
python -m venv .local/gis-venv
.local/gis-venv/Scripts/python.exe -m pip install -r scripts/gis-requirements-lock.txt
```

Do not rerun acquisition/sealing against populated destinations. For an explicitly requested fresh comparison acquisition, use a new name with `replay_public_gis.py`. It pins OSM discovery to its recorded base timestamp and preserves the pilot's historical query. Live USGS/NYS catalogs can change, so replay responses are not promised to be byte-identical. The archived bytes and hashes are the reproducible baseline. New snapshots need their own review and manifest before processing; the replay tool intentionally does not approve them.

SHA-256 detects local changes, not authenticity independently of HTTPS. Each response hash was recorded at download and checked again before sealing. JSON/XML response bodies and GeoTIFFs were saved without GIS modification. Requests uses normal HTTP content decoding.

## Pilot and inventory

Bounds (WGS84 west, south, east, north): **[-73.683585, 42.728278, -73.675583, 42.730755]**, approximately **655 × 275 meters**. Method: combined complete footprints of the seven exact OSM building-name matches, with 50 m geodesic outward margins and outward rounding. This is an acquisition envelope, not clipped geometry. Adjacent buildings are intentionally retained.

OSM historical query: **2026-10-10T04:03:46Z**. The later `timestamp_osm_base` in the response describes the server database, not the requested historical timestamp.

| Inventory | Entire recursive response | Intersects pilot, nonrelations |
| --- | ---: | ---: |
| Nodes / point coordinates | 3363 | 2067 |
| Ways | 741 | 594 |
| Raw relations | 4 | Not geometrically assembled |
| Tagged building elements | 28 | 27 |
| Path / footway / pedestrian ways | 243 | 243 |
| Steps ways | 52 | 52 |
| Road ways | 196 | 53 |
| Entrance-tagged elements | 58 | 45 |

The 28 building elements include 27 ways and one multipolygon relation. Relation dependencies retain complete bus routes and university boundaries, so the raw response extends beyond the pilot. Counts are source elements, not distinct physical paths. Classification of nonrelation ways for inspection yielded 711 lines and 30 polygons (564 lines and 30 polygons intersecting pilot); this is not a general OSM relation converter.

Indoor and level-tagged paths are present. Preserve `level`, `layer`, `bridge`, `tunnel`, indoor tags and node membership in future processing. Coordinate overlap does not imply a routable connection. All tags are preserved in raw data; wheelchair tags occur on only four pilot elements. Missing values remain unknown. The JSON inventory lists every encountered accessibility-related tag value and count.

## Footprint comparison

All seven OSM targets are closed, valid, fully within the pilot, and have plausible nonzero footprint areas. This is a source consistency check, not surveyed ground truth.

NYS returned **27 complete polygons**, all NYSERDA records citing **2014 NYS orthoimagery**. Actual response and layer CRS are **EPSG:26918** despite stale generic service prose mentioning Web Mercator. The county overview reports 2010–2017 across the county, not current campus geometry. Useful actual fields are `OBJECTID`, `COUNTYNAME`, `MUNINAME`, `NYSGEO_SOURCE`, `SOURCE`, `SOURCEDATE`, and `SOURCEID`. Address fields mentioned in generic service prose were not returned by this layer.

| Target | OSM area, m² | Best NYS overlap IoU |
| --- | ---: | ---: |
| DCC | 4905 | 0.710 |
| JEC | 3999 | 0.789 |
| Folsom Library | 2882 | 0.609 |
| Greene Building | 975 | 0.759 |
| Amos Eaton Hall | 965 | 0.771 |
| Lally Hall | 442 | 0.694 |
| Rensselaer Student Union | 4209 | 0.548 |

IoU is intersection area divided by union area for the best individual NYS polygon, measured in memory in EPSG:26918. DCC overlaps two NYS polygons. It is not an accuracy score or a reason to snap/merge boundaries. OSM edits can be newer without indicating a new survey. Recommendation: retain OSM as the initial source and NYS as independent reference; resolve outline differences explicitly before any source substitution. No conflict-resolution policy or merge was applied.

## Elevation decision

TNM returned two 1 m products and no Original Product Resolution product for this pilot. Both downloads are one standard tile, approximately 10 km square, rather than whole regional datasets.

| Product | Published | Download | Valid pilot pixels | Decision |
| --- | --- | ---: | ---: | --- |
| `USGS_1M_18_x60y474_NY_FEMAR2_Central_2018_D19.tif` | 2024-01-04 | 334,705,804 bytes | 180236 / 180236 | Selected |
| `USGS_1M_18_x60y474_NY_Hudson_D22.tif` | 2024-10-09 | 76,320,460 bytes | 4996 / 180236 | Rejected: 97.23% NoData |

Both have **10012 × 10012** float32 cells, **1 × 1 m** resolution, **EPSG:26918** horizontal CRS, and **-999999** NoData. Native bounds are approximately **[599994, 4729994, 610006, 4740006] m**; exact floating-point bounds and WKT are recorded in the inventory. Elevations are **NAVD88 meters** per product metadata. Selected-tile pilot range is **48.973274–82.300835 m**, computed from native pixel centers inside the WGS84 pilot envelope without resampling or writing a clipped raster. Hudson's small valid portion ranges **71.695831–80.171036 m**.

The selected tile's own XML reports temporal extent **2019-01-04 to 2020-09-25**. The project name's “2018” is not proof of the actual collection date. TNM's first vendor link leads to Block 1 metadata describing Niagara/Westchester, with a 10 cm RMSEz design class; that does not establish achieved accuracy or collection dates at RPI. Tile-specific metadata defers accuracy to the original project records. **Exact campus flight date and measured accuracy remain unresolved.** Hudson metadata lists 2022-11-08 to 2023-04-15 and has blank measured-accuracy fields. These limitations are preserved rather than filled with assumptions.

NYS elevation catalog was reviewed. Its 2022 Hudson metadata was inspected, but redundant statewide lidar, orthoimagery and road datasets were not added. Bare-earth DEMs do not resolve curb cuts, individual steps, bridges or indoor floors reliably enough to assert accessibility.

## CRS and terms

Recommend **EPSG:26918 — NAD83 / UTM zone 18N**, in meters: RPI is within zone 18N, and both the selected standard DEM and the NYS sample already use it. OSM remains WGS84 degrees. No source was reprojected or rewritten; in-memory transforms were used only for overlap and raster-window measurements.

A later processor must record its actual PROJ operation, grid availability and stated accuracy. WGS84, NAD83 and NAD83(2011) must not be treated as survey-equivalent merely because numerical differences appear small. Preserve vertical NAVD88 separately; no ellipsoid/geoid conversion has been performed. No Blender origin offset has been selected.

- OSM: [ODbL 1.0 and attribution](https://www.openstreetmap.org/copyright), © OpenStreetMap contributors.
- USGS: [public-domain data policy](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits); credit USGS and originating agencies, preserve limitations.
- NYS: original [service usage terms](https://gisservices.its.ny.gov/arcgis/rest/services/BuildingFootprints/FeatureServer/info/iteminfo?f=pjson) are archived in `raw/nys/iteminfo.json`. They provide as-is terms and attribution, not an explicit standardized redistribution license. Do not assume CC0 or merge/relicense this source without resolving terms.

## Completion and next step

All core data downloads succeeded without authentication, interactive viewers, or bypassing access restrictions. A county metadata query initially used the wrong field; it was corrected using the layer schema. EPSG's website returned 403 in the browser; no bypass was attempted, and CRS evaluation used the installed PROJ/EPSG database and source metadata instead. No manual data download is currently needed. If tile-local accuracy is required, begin with the saved ScienceBase item and its original project metadata links.

Next: verify the integrity seal, then implement a deterministic source-ID-preserving parser and layer validator under `gis/cleaned/`. Preserve complete node/member topology and multilevel semantics, explicitly review boundary-crossing features, keep NYS separate, and document datum operations. Stop before Blender until those derived layers validate. Existing Blender importer and scene validator remain untouched placeholders.
