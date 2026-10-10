# Pilot pass 02: pavement and campus landmarks

Working file: `rpi_lowpoly_20261010_pass02_v03.blend`.
Overview: `../../renders/rpi_lowpoly_20261010_pass02_overview_v03.png`.
Validation: `rpi_lowpoly_20261010_pass02_validation.json`.
Branch: `codex/pilot-landmarks-pavement-pass02`. Main is not modified.

## Presentation changes

- Added 316 flat pavement meshes following the existing presentation terrain. Each ribbon retains the exact XY of every original display centerline station and its source ID. Original curves are retained, hidden, and recoverable.
- Kept the prior illustrative widths: roads 4 m, paths 1.6 m, stairs 1.5 m. Limited miter joins avoid extreme spikes at bends. Separate source features are not joined, snapped or promoted to network connections.
- Added symbolic stair crossbars. These are cartographic hatching, not measured physical tread positions or counts.
- Added a shallow eight-strip roof and glazing/mullion colors to EMPAC, plus a broad cedar-hull-inspired facade motif. The motif is not a surveyed interior hall, entrance, or claim of its exact placement.
- Added a pitched chapel roof, granite palette and stylized Gothic window bays to VCC.
- Added concrete materials and three dark window bands to Folsom Library.
- Added eight building labels, a grid-north arrow, a surface legend and clearer attribution. A copied camera provides closer framing at 2100 x 1500. The earlier full-extent camera and all boundary-crossing features remain in the scene.

The original 28 building meshes retain their exact vertices, transforms, topology, source IDs and metadata. Roof additions are clipped inside source footprints. Facade marks follow source wall segments, with a presentation-only 0.025 m solidify relief (0.015 m on the cedar motif) to avoid coplanar flicker. Their relief does not modify protected footprints.

## Reference review, 2026-10-10

- EMPAC: https://grimshaw.global/projects/education-and-science/empac/ and https://empac.rpi.edu/about/building. Design cues: glazed exterior, curving roof, warm cedar hall. Roof rise is a 4 m visual estimate, not a measured architectural dimension.
- VCC: https://archives.rpi.edu/institute-history/building-histories/chapel-voorhees-computing-center. Design cues: former Gothic chapel and light granite. Pitched-roof rise is a 7 m visual estimate; window spacing is stylized.
- Folsom: https://archives.rpi.edu/institute-history/building-histories/folsom-library and the exterior image associated with https://news.rpi.edu/content/2018/02/12/center-global-communication-and-design-announces-new-name-and-broader-mission. Concrete and horizontal window bands provide recognition. Existing estimated height is retained.

References inform low-poly motifs; no photographs or textures were copied into the project. Detailed facade surveys and current architectural drawings have not been obtained.

## Preservation checks

The saved original baseline is compared exactly for all 455 baseline objects: world transforms, world-space mesh vertices, edges, faces, loops, metadata, nested collection hierarchy and shared object memberships. Full source-graph text including ordered relation members remains unchanged.

All 344 original building and line display objects also retain their geometry and metadata. The validator permits only hiding the earlier line displays. Materials change on the three landmark displays; the protected GIS meshes are untouched.

All 7,747 centerline stations retain **zero XY difference**. Pavement vertices follow the unchanged triangulated 4 m terrain with a 0.10 m display lift; maximum float32 conformance residual is about **0.0000113 m**, below the explicit 0.0002 m tolerance. These numbers are computational checks, not positional accuracy or measured pavement elevation. Label rectangles do not overlap.

The GIS validator passed again: 47 sealed raw files, 4,108 source elements, 4,488 ordered segments and all 78 boundary reviews. All 27 NYS comparison footprints stay separate. The documented datum operation and its stated 4 m accuracy are unchanged. No new source data, CRS transformation, pavement widths, accessibility values or route connections were inferred. The 32 indoor/multilevel features omitted from the surface display are retained in full in the source collections.

## Recovery and scripts

- `../checkpoints/rpi_lowpoly_20261010_pass02_before_changes.blend`: unique checkpoint saved before edits, after the original baseline passed.
- `rpi_lowpoly_20261010_pass02_v01.blend`: first completed pass, before contrast and cedar-motif refinement.
- `rpi_lowpoly_20261010_pass02_v02.blend`: contrast and cedar-motif refinement, before decorative normal correction.
- `rpi_lowpoly_20261010_pass02_v03.blend`: refined working result. Original files and master directory remain untouched.
- `../../scripts/prepare_pass02_landmarks.py`: deterministic roof parameters and footprint-clipped mesh preparation, using the existing GIS Python environment.
- `../../scripts/blender_pass02.py`: presentation recipe and substantive validator.
- `../../scripts/build_pass02_run.py --mode validate`: prepares safe-mode-compatible inline code under `.local/`; pass that code to the live Blender MCP execution tool. It uses the current source scene and embedded baseline. Apply mode refuses already-created checkpoint/output names.

Blender safe mode remains enabled. No new socket, firewall, telemetry, external asset service or startup setting was used. A synchronous render tool timeout did not cancel rendering; the output file was checked after Blender completed it.

## Remaining accuracy work

This pass improves depiction and legibility; it does not establish new geographic accuracy. A subsequent evidence pass should compare source IDs against dated orthophotography and campus engineering records, measure pavement widths where supported, and review curb ramps, crossings, stairs and entrance connections. Record discrepancies before proposing any authorized XY correction. Accessibility remains unknown unless independently verified; no visual connection is proof of a navigable route.
