# Pilot imagery and elevation evidence review

Prepared 2026-10-10. This is a separate review package, not a corrected map or a routing dataset. Eight candidates retain source IDs and complete source records: five building observations and three pavement review windows. The original OSM and NYS layers remain separate and unchanged; unknown accessibility values remain unknown.

## Findings and next modeling pass

See [the overview](source_overlay.png), paired building panels, and [review annotations](discrepancy_review.json).

- Greene: hipped roof and dormer forms offer a useful recognition improvement.
- JEC, Union and DCC: roof regions/extensions need separate massing treatment. Heights remain unverified.
- Folsom: roof-edge versus footprint differences require overhang/relief and positional-uncertainty review before any coordinate change.
- Folsom–VCC plaza, JEC–DCC courtyard and Union approaches: pavement widths, plazas and obscured connections need evidence beyond the existing centerlines. Review windows are annotations, not new pavement polygons. Linked path/stair/road records are complete, not clipped.

The next safe scene pass can add reference-supported roof silhouettes on a new checkpoint while preserving footprints. Accurate pavement boundaries, clear widths, curb cuts, slopes, entrance levels and route connectivity still require ground-level or survey evidence. No accessibility claims follow from aerial imagery.

## Source selection and provenance

The new acquisition is under `gis/acquisitions/evidence_20261010_01/`, outside `gis/raw/`. Its SHA256SUMS seals 86 source and HTTP-sidecar files. Each HTTP sidecar records exact URL, UTC acquisition time, response metadata, byte count and SHA-256. The acquisition script now refuses further writes to this sealed snapshot. A later acquisition must use a new snapshot.

Two native NYS 2024 orthophoto ZIPs cover the study. Each contains four-band JPEG2000 imagery at one US survey foot per pixel (0.3048006096 m), EPSG:6537, NAD83(2011) / New York East (ftUS). RGB bands 1–3 were mosaicked without resampling; source ZIPs are unchanged. Spring 2024 is the service-level capture period; the exact campus flight day and achieved positional accuracy are unresolved. The queried 2025 index layers returned no pilot coverage. This supports selecting the available 2024 coverage, not a claim that every imagery provider was searched.

Official references: [NYS imagery program](https://gis.ny.gov/orthoimagery), [2024 coverage](https://gis.ny.gov/2024-orthoimagery), [NYS FAQs](https://gis.ny.gov/orthoimagery-faqs), [NYS LiDAR](https://gis.ny.gov/lidar). Archived copies and service metadata accompany the acquisition. NYS imagery is attributed to NYS ITS Geospatial Services and supplied as-is; no standardized redistribution license or CC0 dedication is asserted. Free download is not itself a license. Directory-listing requests returned 403; official direct tile links succeeded. License clarification remains relevant before redistributing imagery outside this evidence archive.

Two USGS FEMA Central Block 4 point-cloud tiles were inspected. Header CRS is EPSG:6350 (NAD83(2011) / Conus Albers), with EPSG:5703 NAVD88 heights in metres and GEOID12B. Project metadata reports collection 2019-04-25 through 2020-09-25; a project name containing 2018 is not the capture date. USGS project metadata lists use constraints as “None,” with temporal/fitness caveats; retain USGS attribution. The project design class is 10 cm RMSEz, not verified campus accuracy.

The two point clouds contain 1,024,317 eligible AOI returns after excluding withheld/overlap flags. Their bounding boxes cover 99.9976% of the review AOI; that does not prove continuous return coverage. Classes present in the AOI are unclassified (1), ground (2), and low noise (7). There are **no class-6 building returns**, so all per-building classified roof-elevation samples remain null. Do not derive heights from unclassified points without a separate, validated segmentation method.

The refreshed USGS DEM catalog returned the same two 1 m products already reviewed. The newer Hudson D22 DEM remains unsuitable for full-pilot terrain: the earlier validated pilot review found 97.23% NoData. Newer point-cloud catalog/index hits are discovery evidence only; undownloaded tiles have not been validated. The existing terrain was not replaced.

## Datum and geometry handling

Evidence comparisons use four archived NOAA NADCON5 grids from `cdn.proj.org`. The process-local, network-disabled transformation is NAD83 → HARN → FBN → NSRS2007 → NAD83(2011), with stated operation accuracy 0.2 m. Full pipelines, PROJJSON and grid hashes are in [imagery_review.json](imagery_review.json) and [elevation_review.json](elevation_review.json). Imagery conversion ends in EPSG:6537; LiDAR comparison ends in EPSG:6350. No vertical operation occurs: LAS Z stays native NAVD88/GEOID12B metres. Neither dataset uses a local origin offset.

The original pilot's EPSG:26918 coordinates and original datum operation are unchanged. Its inherited 4 m stated datum-operation accuracy remains relevant; the new 0.2 m operation does not improve the source coordinates. Maximum imagery transformation round-trip error was 1.08e-7 m. Roof relief, overhangs, shadows, trees and different capture dates prevent automatic footprint or path corrections.

The evidence AOI is a rectangular 50 m margin around the same seven projected target footprints, not exactly the earlier geographic envelope. Plot viewports crop display only. Original features, ordered topology, multilevel semantics and boundary dependencies are retained in the source layers and embedded review records.

## Validation and reproduction

[Integrity report](integrity_validation.json): original 47-file raw seal and deterministic pilot validation pass, including 4,108 source elements, 4,488 source segments, 78 boundary crossings and 27 independent NYS footprints. All 12 tracked Blender files match their committed LFS SHA-256 hashes. Existing importer and scene-validator placeholders are untouched. This proves no scene bytes changed; it is not a new semantic Blender validation.

The elevation and discrepancy analyses reproduce byte-identical JSON outputs. `source_hashes.json` records inputs present at imagery-generation time; the acquisition SHA256SUMS is the authoritative complete snapshot inventory, including subsequently completed LiDAR downloads.

From the repository root, use the pinned environment in `requirements-evidence.txt`:

```powershell
.local/gis-venv/Scripts/python.exe scripts/build_evidence_review.py --out .local/new-imagery-review
.local/gis-venv/Scripts/python.exe scripts/finish_evidence_review.py --out .local/new-elevation-review
.local/gis-venv/Scripts/python.exe scripts/audit_evidence_review.py
```

Output directories/files must be new; the audit uses a unique repeatability directory and checks the saved report on later runs. No Blender scene was edited or rendered during this evidence pass. The overview is a GIS comparison image.
