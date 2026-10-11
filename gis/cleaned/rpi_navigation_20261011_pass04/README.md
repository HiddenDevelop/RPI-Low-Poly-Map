# JEC–DCC–Greene navigation milestone

2026-10-11 · branch `codex/jec-dcc-navigation-pass04`

[Interactive plan review](index.html) · [Blender scene](../../../blender/working/rpi_navigation_20261011_pass04_v01.blend) · [District render](../../../renders/rpi_navigation_20261011_pass04_district.png) · [North-side bridge view](../../../renders/rpi_navigation_20261011_pass04_north_walkways.png) · [Campus overview](../../../renders/rpi_navigation_20261011_pass04_overview.png)

This is a navigation-focused prototype and evidence inventory, not a validated directions service. The plan inspector supports layer filtering, feature selection, pan/zoom, building focus, source attributes, unknown values and landscape-review toggles. No route directions are offered.

## Implemented

- Two source-tagged bridge spans now have decks, railings and endpoint support cues. Thirteen elevated line features are displayed, rather than omitted as in the surface-only overview.
- Sixty-nine complete walkway/stair features receive source-aware presentation. Concrete, concrete slabs and paving stones have distinct materials; slab/paver joints and stair hatching are symbols, not measured joints/treads. Missing surfaces remain unknown.
- Fifteen visible entrance markers correspond to source nodes; the plan layer retains all 17 entrances, including lower-level entries. They do not assert wheelchair access or physical doorway dimensions.
- Two manually interpreted canopy centers receive faceted tree representations. These are approximate 2024 canopy locations, not surveyed trunks or a complete tree inventory. No random tree placement was used.
- A candidate courtyard pavement envelope is available only as a separate plan-review layer. It is not presented as a measured pavement boundary or used to create route edges.
- A dated closure review and an archived official RPI notice accompany the model and plan inspector.

The unchanged building extrusions can still obscure some covered walkways in 3D. Use the plan view and north-side render to inspect the connections. Building undercrofts, exact bridge decks, physical stairs and canopy structures require architectural/field evidence before further refinement.

## Provenance, coordinate systems and unknowns

The original pilot OSM features are copied completely, including IDs, source tags, timestamps, ordered node lists and scope. OSM attribution and original acquisition/license notes remain in `gis/ACQUISITION.md`. NYS footprints remain separate; no NYS/OSM merging occurs. No new OSM download was silently substituted.

The review AOI is EPSG:26918 bounds `[607922,4731519,608169,4731709]`, in metres. It selects features by intersection but never clips them: 21 cross its boundary and retain their full geometry and nodes. Display coordinates retain the existing `[608100,4731600,0]` origin and metre scale.

Landscape interpretation references the sealed NYS Spring 2024 JEC imagery panel from the previous evidence pass. The image SHA-256, selected native EPSG:6537 canopy coordinates, datum pipeline and uncertainty are recorded in `landscape_review.json`. The archived NADCON5 horizontal operation has stated 0.2 m accuracy; this does not establish source or manual digitizing accuracy and does not remove the original datum uncertainty. No vertical datum transformation was performed. NYS ITS Geospatial Services attribution and as-is/no-standardized-license notes remain in the prior evidence report. No imagery textures were imported.

Only **one** selected line has a numeric width tag (2 m, unverified). Other display ribbons use the explicitly illustrative 1.6 m default. Of 76 selected line features, 49 have unknown surface, 15 concrete, six concrete slabs and six paving stones. Widths and surface tags are not evidence of accessible clearances.

Elevated display Z is a uniform **73.8 m presentation parameter**, not an elevation inferred from `layer=1` or `level=1`, and not a measured NAVD88 deck height. Original ground presentation comes from the unchanged 4 m DEM mesh. Rails are 1.05 m high and supports occur at mapped span endpoints; these are illustrative dimensions. No slope, clearance, support location between endpoints, or wheelchair value is inferred. Steps retain symbols rather than invented physical tread counts. Underground and multilevel transition features remain visible in the plan inventory; they are not forced onto the terrain.

## Closure review

[RPI's September 14 upper-deck closure notice](https://administration.rpi.edu/announcements/dcc-jec-upper-deck-walkway-closure) was reviewed and archived on 2026-10-11 in `gis/acquisitions/navigation_20261011_01/`, with acquisition timestamp, SHA-256 seal and RPI copyright attribution. It estimated approximately three weeks and discussed partial reopening; it does **not** confirm a reopening date. The current status and exact affected OSM segment set remain unconfirmed, so this is a review warning rather than a silent edit to source access tags. Follow current campus signs and designated detours.

The official notice links exterior and interior detour maps hosted on Box. The web tool could not retrieve those linked documents. Their routes were not reconstructed from guesses or substituted with an automatically generated accessible route.

## Topology review

The inventory preserves 95 features, 307 ordered source segments and 304 incident source nodes. All 17 entrances share a source node with at least one selected way. This is a structural observation, not a verified accessible entrance connection.

Three geometric crossings have no shared source node: each involves a bridge/elevated feature or a tunnel, so they remain disconnected. No XY intersection was snapped or made into a graph junction.

Eight shared nodes have mixed level/layer descriptions:

| Source node | Review needed |
|---|---|
| 1208043799 | Level 1 meets an unspecified-level way. |
| 13208046514 | Level -1 meets explicitly tagged 0/-1 stairs. |
| 13208046515 | The same stairs meet level 0, layer -1. |
| 2032237534 | Layer -1 meets an unspecified-layer way. |
| 2870374473 | Bridge layer 1, walkway level 1 and an unspecified-level way share a node; level and layer are not interchangeable. |
| 2872820222 | Bridge layer 1 meets a layer -1 way. Confirm the physical building entry/transition. |
| 2872820224 | Layer -1 / level 0 meets an unspecified-level way. |
| 2882579034 | Layer 1 meets an unspecified-level way. |

These records remain unchanged and flagged. `source_topology.json` contains full incidence details, segment provenance and crossing geometries. No graph is marked routing-ready.

## Validation and recovery

[Independent GIS checks](independent_validation.json) compare all 95 full records, all 307 ordered segment endpoints/coordinates, incident nodes, source unknowns and output hashes against the original pilot. Rebuilding the six generated GIS JSON files in a separate directory produced byte-identical results. The original pilot validator still passes all 47 raw hashes, 4,108 graph elements, 4,488 segments, 78 pilot boundary crossings and 27 independent NYS footprints.

[Scene validation](../../../blender/working/rpi_navigation_20261011_pass04_validation.json) compares all 1,257 prior objects and 21 prior collections: world/local transforms, world-space vertices, edges/faces/loops, curve points, source metadata, hierarchy and linked memberships. Source geometry and metadata compare exactly. The only permitted old-object changes are visibility of replaced display ribbons/hatches. New deck inventory, faces, width metadata and 1,508 source-derived centerline stations are checked; the maximum float serialization difference is 0.00000762 m. This tolerance does not permit moving original geometry.

A unique [pre-change checkpoint](../../../blender/checkpoints/rpi_navigation_20261011_pass04_before_changes.blend) and [full compressed baseline](../../../blender/checkpoints/rpi_navigation_20261011_pass04_baseline.json.gz) precede changes. The saved final scene was reopened and validated. Work used an isolated Blender 5.2.2 background process because live MCP was unavailable; the user's open scene was not edited. Master files, original GIS, previous checkpoints, importer/validator placeholders, firewall and add-on configuration are unchanged.

Three renders were visually inspected. The HTML viewer's JavaScript passes `node --check`; automated browser preview was blocked by the browser's local-file URL policy. No browser-interaction or visual-layout test is claimed, and no workaround was used to bypass that policy.

## Remaining gate to usable navigation

Obtain current detour plans and confirm bridge reopening; measure deck/landing heights and transitions; verify the eight mixed-level nodes; survey clear widths, slopes, curb cuts and entrance operation; distinguish physical stair/ramp/elevator connections; verify pavement boundaries and a fuller tree/planter inventory. Then implement and test routing rules with explicit handling of unknown accessibility. More polygons alone cannot resolve these gaps.

Reproduce with the pinned evidence GIS environment and new output directories:

```powershell
.local/gis-venv/Scripts/python.exe scripts/prepare_navigation_milestone.py --out .local/new-navigation-review
.local/gis-venv/Scripts/python.exe scripts/validate_navigation_milestone.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup blender/working/rpi_navigation_20261011_pass04_v01.blend --python-exit-code 1 --python scripts/blender_navigation_pass04.py -- validate
```

Apply/render/build scripts refuse existing output artifact names. Use a new run ID for subsequent passes.
