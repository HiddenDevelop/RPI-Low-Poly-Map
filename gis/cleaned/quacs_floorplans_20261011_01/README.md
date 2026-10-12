# QuACS floor-plan evidence review

Reviewed 2026-10-11 at pinned commit `08c82580638b3e9a3816802f3e1ba98a30383f13`.

## Decision

Useful historical architectural evidence. Retain alongside the official facilities/detour evidence strategy; do not import as current routing geometry. Acquired 17 sheets: JEC 1000-7000 and roof, DCC 100-300, Greene basement, 100-400 and mezzanine. All downloaded PDFs were checked against Git blob SHA-1 and sealed with SHA-256. Source files live in `gis/acquisitions/quacs_floorplans_20261011_01/` and are separate from both original raw GIS and NYS evidence.

Visually reviewed the complete JEC 3000, DCC 300 and Greene 100 sheets, using Poppler at 1500 pixels. Poppler warned about unavailable Symbol and ArialUnicode display fonts; walls, door swings, stairs and relevant labels were visible. Other sheets have text/metadata inventory only, not complete visual review.

## Findings from the reviewed sheets

* JEC 3000: drawn balcony zones 3000B, 3000C and 3000D, columns, stairs, vestibules and open-to-below areas. These are useful references for replacing overly solid display massing with level-specific openings in a future checkpoint. Elevator label 3-E is historical evidence of a shaft, not proof of a currently usable accessible route.
* DCC 300: lecture-hall footprints, lobby/corridor circulation, stairs, vestibules and elevator 3-E are shown. The plan helps interpret where exterior walkways meet the building, but does not uniquely identify an OSM node or prove the current bridge connection.
* Greene 100: elevator 1-E, stair 100E and vestibule 100F appear together at the right-hand end of the sheet. This is a candidate area to investigate for the JEC-facing approach; sheet orientation and the precise source-node match remain unverified.
* All three reviewed sheets state PLOTTED 8/8/2006. Their current condition is unknown. A plot date is not a survey or last-renovation date.

## Coordinates, scale and rights

JEC 3000 and DCC 300 state 1 inch = 30 feet; Greene 100 states 1 inch = 20 feet. PDF page coordinates are points; printed scale is not an established geographic transform. No geographic CRS, geodetic datum, elevation datum, local campus origin or control points have been established. No datum operation, georeferencing, snapping or coordinate conversion has been performed. Ground coordinates and route widths remain null. Printed room areas must not be substituted for measured passage widths.

Repository LICENSE is MIT, copyright 2020 quacs, and is retained verbatim. Drawings identify INSITE Visual-FM 3.1 and .ins drawing filenames. The repository README does not explain original acquisition or establish separate original drawing authorship/rights. Record that uncertainty; do not assert the plans are public domain or current official accessibility certification.

## Source-ID crosswalk review queue

| Existing source | Plan evidence to compare | Status |
| --- | --- | --- |
| osm/way/104737241 | JEC 3000 balcony bands | Candidate only; no geographic alignment |
| osm/way/284529300; osm/node/2872820222 | JEC 3000 / DCC 300 exterior approaches | Connection and level transition unresolved |
| osm/way/104737300; osm/node/2870374473 | JEC 3000 / Greene 100 approach | Connection and level transition unresolved |

OSM layer is not a floor number. Preserve source level, level:ref and layer independently; do not map 3000 or 300 to OSM level=3 automatically. No new junctions at geometric crossings. No source nodes, ordered way members, relations, boundary-crossing features, accessibility unknowns or protected Blender objects were changed. Current closure evidence remains in force as an unresolved operational status; these historical drawings do not confirm reopening.

## Next implementation gate

Compare the historical balcony/vestibule outlines with current official detour plans and imagery, establish documented orientation/control correspondences with residuals, and confirm current entrances/elevators. Then prepare a separately reviewed display-only undercroft proposal within unchanged building XY footprints. Only after topology/metadata checks should a unique Blender checkpoint receive changes. Navigation remains unavailable until route connectivity and accessibility are validated.
