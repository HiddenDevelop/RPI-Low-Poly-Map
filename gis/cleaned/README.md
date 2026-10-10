# Validated RPI pilot source layers

The current output is `pilot/`. Parser: `../../scripts/prepare_pilot_gis.py`.
Read-only validator: `../../scripts/validate_pilot_gis.py`.

## Result and validation scope

The immutable raw seal verifies all **47 recorded files**. The parser retains all **4108 OSM elements** (3363 nodes, 741 ways, 4 relations) and **4488 ordered source way segments**. The seven requested building footprints are closed, valid, and fully inside the pilot. NYS has **27 separate footprints**. No feature was repaired, dropped as invalid, snapped, clipped, simplified, or merged with another source.

| Layer | Features | Meaning |
| --- | ---: | --- |
| `pilot/osm/buildings.json` | 28 | 27 building ways plus one assembled building relation |
| `pilot/osm/paths.json` | 243 | Pedestrian source ways, including indoor/multilevel ways |
| `pilot/osm/roads.json` | 53 | Intersecting road/service-road ways |
| `pilot/osm/stairs.json` | 52 | Source `highway=steps` features |
| `pilot/osm/landcover.json` | 3 | Source land-use/land-cover/natural features |
| `pilot/osm/entrances.json` | 45 | Source entrance-tagged features |
| `pilot/osm/accessibility.json` | 49 | Actual accessibility-related tags or elevator features; not a claim that these are accessible |
| `pilot/osm/other.json` | 2214 | Remaining intersecting source elements, including geometry nodes and relations |
| `pilot/nys/buildings.json` | 27 | Native NYS footprints, no OSM source fusion |

Layers can overlap by source ID (for example a path with a tactile-paving tag). They are views of the source graph, not disjoint counts of physical objects. Do not sum layers to infer a unique feature count or import supporting nodes/area member ways as duplicate buildings.

## Format and topology contract

The `.json` layers use explicit schema `rpi-source-layer-v1`, **EPSG:26918**, meter units and zero local origin offset. They contain GeoJSON-shaped geometry objects, but **are not RFC 7946 GeoJSON**, since RFC 7946 expects WGS84 longitude/latitude. Consumers must read the CRS explicitly and must not treat these coordinates as longitude/latitude.

Every feature has a stable namespaced ID (`osm/node/…`, `osm/way/…`, `osm/relation/…`, or `nys/building/…`) and an exact `source` record preserving all original fields, tags, version/timestamp, ordered node IDs or ordered relation members. The source graph includes complete off-campus dependencies; no node is deduplicated by coordinates. Each source way segment retains its original index and endpoint IDs. This **is not a routable graph** and introduces no cross-feature connectivity.

Multipolygon assembly joins only identical endpoint node IDs. It may reverse a member for ring traversal, recording the orientation and original member index; the original member and node arrays remain untouched. Missing links, branch ambiguity, unsupported multipolygon roles, invalid rings or unowned holes fail. Non-polygon relations use ordered GeometryCollections, preserving repeated members. No line merging or polygon repair is used.

All raw tags remain in `source.tags`. `semantics` is only a convenient copy of present relevant strings, including `level`, `level:ref`, `layer`, `indoor`, `bridge`, `tunnel`, `ramp`, `wheelchair`, and access tags. Multi-value level strings are not normalized, sorted or interpreted. Unknown values stay absent. Neither OSM levels nor elevation strings become geometric Z. NYS's native Z values remain in its source rings, with vertical semantics explicitly unknown; the derived view uses unchanged XY only.

## Explicit boundary review

The pilot envelope is west/south/east/north **[-73.683585, 42.728278, -73.675583, 42.730755]**. Scope classification is source based; the complete feature is retained whenever it intersects the pilot.

`pilot/boundary_review.json` lists every crossing feature, its source ID, name, layer membership, bounds, semantics and decision. There are **68 OSM crossings** and **10 NYS crossings**; none is cropped. The complete OSM graph has **2597 inside**, **68 crossing**, and **1443 outside-dependency** elements. Outside dependencies are listed by ID and retained in `osm/source_graph.json`, not promoted into the pilot layers.

| OSM crossing category | Count | Decision |
| --- | ---: | --- |
| Paths | 32 | Retain all vertices, nodes and source tags; two also appear in the accessibility view |
| Roads | 15 | Retain full source segments; source endpoints remain intact |
| Buildings | 11 | Retain full footprints beyond the envelope |
| Stairs | 2 | Retain full source geometry; no elevation or accessibility inference |
| Landcover | 2 | Retain full source boundaries |
| Other | 6 | Preserve supporting features and complete relation graphs |

Examples reviewed: Walker Laboratory, Russell Sage Laboratory, the Quadrangle, EMPAC and CBIS extend beyond the envelope; keeping their full footprints avoids creating false building walls at the pilot edge. Paths `osm/way/1357936375` and `osm/way/1357936377` retain `layer=-1`. The RPI university relation and both bus-route relations cross the boundary; the bus routes retain **92** and **111** member occurrences respectively, including repeats and direction roles. The dining-hall building relation is inside. All seven named pilot buildings remain inside.

NYS classification uses its native projected geometry against the pilot envelope transformed with 32 subdivisions per edge. This densifies only the analytical selection boundary, never source geometry. There is no proposed clipping boundary for source features. A future bounded display can mask presentation separately only after review; it must not replace authoritative geometry with cropped paths or footprints.

## Datum and elevation decision

`pilot/datum_operations.json` records the actual PROJ pipeline, complete operation JSON, stated accuracy, versions, PROJ database hash and unavailable grid operations. Input axis order is longitude/latitude; output is easting/northing.

- OSM uses **inverse EPSG:1188 (NAD83 to WGS84 (1)), then EPSG:16018 (UTM zone 18N)**. The pinned operation has **4 m stated accuracy**, no grid dependencies, no ballpark transform, and network access disabled. It does not assert that OSM coordinates themselves are accurate to 4 m.
- Locally unavailable 2 m alternatives require `us_noaa_nyhpgn.tif` or `us_noaa_nehpgn.tif`. No grids were downloaded or silently substituted. A change to the datum operation requires a new derived run and review.
- NYS uses identity **EPSG:26918 → EPSG:26918**. No source matching, snapping or alignment adjustment was applied.
- No vertical operation or Blender local-origin conversion was performed. The selected USGS raster is referenced with its raw hash in `terrain_reference.json`; it has not been copied, resampled, clipped or used to drape multilevel paths. NAVD88 is not an ellipsoidal height.

Source geographic uncertainty, unknown datum realization/epoch, footprint disagreements, NYS terms and the previously documented elevation date/accuracy limitations persist. A numerically precise transform check is not a survey-accuracy or accessibility guarantee.

## Reproduce and verify

From the repository root:

```powershell
.local/gis-venv/Scripts/python.exe scripts/validate_pilot_gis.py gis/cleaned/pilot
.local/gis-venv/Scripts/python.exe -m unittest discover -s scripts -p test_pilot_gis.py -v
```

To build another run, choose a **new** output directory:

```powershell
.local/gis-venv/Scripts/python.exe scripts/prepare_pilot_gis.py --output gis/cleaned/pilot_recheck
.local/gis-venv/Scripts/python.exe scripts/validate_pilot_gis.py gis/cleaned/pilot_recheck
```

Existing output directories are never overwritten. Runtime dependency versions are in `../../scripts/gis-requirements-lock.txt`. Output serialization is sorted and contains no run timestamps or random values. Byte-for-byte reproduction is checked against the current output. Source graph array order follows stable element type/ID ordering, while each source node/member/ring sequence remains original.

Validation checks hashes, all source metadata and IDs, all projected vertex coordinates (1 micrometer comparison tolerance), inverse coordinates (1e-9 degrees), topology, layer completeness, reasonable greater-Troy bounds, empty/invalid/zero-size geometry, source separation, all seven buildings and boundary-review coverage. Those numeric tolerances check computational consistency only. Adversarial tests alter in-memory copies and recompute derived checksums before validation, ensuring semantic checks—not only hashes—reject corruption. Raw sources are never modified by tests.

`pilot/validation.json` is the saved passing report, recomputed by the standalone validator. `manifest.json` hashes inputs, code and derived payloads; the report itself is checked against fresh validation, rather than treated as evidence on its own.

Stop point: GIS source fidelity and layer validation complete. No Blender scene was opened or modified; `scripts/import_gis.py` and `scripts/validate_scene.py` remain their existing placeholders. No accessible routing or visual styling is implemented.
