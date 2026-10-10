# RPI pilot — first low-poly styling pass

Final file: `rpi_lowpoly_20261010_01_final.blend`.
Overview: `../../renders/rpi_lowpoly_20261010_01_final_overview.png` (1800 × 1300).
Validation: `rpi_lowpoly_20261010_01_final_validation.json`.
Blender scene: `RPI_PILOT_rpi_lowpoly_20261010_01`.

## Changes

The live file initially contained only Cube, Camera and Light. The validated pilot was imported into a new scene, leaving those objects and the original scene intact. Existing `scripts/import_gis.py` and `scripts/validate_scene.py` remain unchanged placeholders; this pass uses dedicated preparation and styling scripts.

Created 451 unique GIS source meshes plus a 42,921-vertex presentation terrain mesh. The complete source graph (all 4108 OSM elements, ordered members and source segments) is embedded as JSON in `RPI_AUDIT`, alongside datum metadata. NYS footprints remain a separate GIS comparison dataset and were not merged or imported as duplicate buildings.

Presentation objects are isolated in `DISPLAY_NONAUTHORITATIVE`: 28 flat-roof building extrusions, 316 DEM-following surface-line displays, a soil edge, backdrop, camera, sunlight and captions. Brick, ochre, sand and slate materials provide the warm low-poly palette. All 28 building outline boundaries are preserved without beveling or simplification. No sourced tree locations exist, so no trees were invented.

32 indoor/nonzero-level/underground line features are omitted only from the surface display; their complete source meshes, tags, ordered node IDs and relation membership remain preserved. Rendered lines do not assert accessibility or connectivity. No accessibility values were filled in or reinterpreted.

## Coordinates and estimates

Working CRS: EPSG:26918, meters. Local origin offset is **[608100, 4731600, 0]**. Blender XY equals projected GIS XY minus this offset, with scale 1. The CRS, offset, source records and IDs are stored as custom properties. The underlying GIS retains its original double-precision coordinates.

Blender float32 conversion has a maximum measured XY error of **0.0000243045 m**, below the explicit 0.0001 m import tolerance. Display footprint error is at most **0.0000152027 m**. These are computational tolerances, not geographic accuracy: the GIS datum operation still has a stated 4 m accuracy and source uncertainty remains.

OSM vectors lack authoritative Z. Their hidden source meshes use an explicitly marked zero placeholder, not an inferred floor elevation. Display building heights estimate OSM levels × 3.4 m, or 10.2 m default, clamped to 6–30 m; roof elevations also clear the sampled terrain. These are not measured building heights. Wall bases use the lowest sampled footprint terrain elevation minus 0.5 m.

Display line widths are illustrative: roads 4 m, paths 1.6 m, stairs 1.5 m. Display-only samples along the original straight segments follow the DEM; original vertices and topology remain in the source meshes. Widths are not measured clearances. Line cross sections use low-resolution curves; they are not replacement GIS geometry.

Terrain uses a 4 m low-poly presentation grid sampled from the selected native 1 m USGS DEM; native source rasters remain untouched. Grid XYZ was checked against the supplied sample payload with **zero measured float32 difference**. NAVD88 terrain elevations are not applied to source floor/level semantics. The rectangular display extent includes complete boundary-crossing features and therefore exceeds the seven-building selection envelope.

Final palette refinement changed materials and world strength only: meadow (0.27, 0.40, 0.15), slate roofs (0.075, 0.15, 0.17), sand roofs (0.52, 0.40, 0.24), clay roofs (0.28, 0.085, 0.045), roads (0.19, 0.25, 0.25), paths (0.88, 0.74, 0.48), world strength 0.4. Wall colors are stable per source ID using a weighted character sum. Render uses Cycles, 32 samples, denoising, orthographic scale 1250. The attribution and limitation captions are camera-relative presentation objects.

## Checkpoints and validation

Unique recoverable checkpoints in `../checkpoints/`:

- `rpi_lowpoly_20261010_01_before_data_staging.blend`: original scene before any staging/import.
- `rpi_lowpoly_20261010_01_before_import_retry.blend`: original scene plus preserved input staging.
- `rpi_lowpoly_20261010_01_before_styling.blend`: validated source-only pilot with complete saved baseline.
- `rpi_lowpoly_20261010_01_before_color_refinement.blend`: first styled scene before contrast refinement.

The baseline is stored in the **`RPI_AUDIT` collection custom property `baseline_documents_json`**, inside the before-styling checkpoint and final working file. It contains full world-space vertex arrays, matrices, edges, faces, loops, source metadata and nested/linked collection membership—not merely counts or a placeholder pass flag.

Final checks passed for all 455 baseline objects (452 imported source/terrain objects plus the original three). World transforms, world-space coordinates, mesh topology, source metadata, nested collection structure and shared object memberships are unchanged. Terrain material assignment was allowed; the terrain geometry and metadata are identical. All 451 expected source collection assignments were checked, including objects linked into multiple protected collections. Original scene objects are unchanged. The final UI intentionally shows the pilot scene in camera view.

The raw 47-file integrity seal and derived GIS validator were rerun and passed. No raw GIS file or master Blender file was modified. Before-import and before-styling checkpoints were used to recover two implementation interruptions: cross-scene visibility and Blender 5.2 triangulation returning vertex indices. A JSON list-versus-tuple comparison discrepancy was corrected by canonical serialization; the original baseline values were not changed. Safe mode stayed enabled, with permitted inline operations and bounded JSON transfer batches. No network asset services, telemetry settings, socket exposure or firewall settings were changed.

## Scripts and continuation

- `../../scripts/prepare_blender_style_payload.py`: read-only GIS/DEM inspection and visualization samples.
- `../../scripts/blender_pilot_lowpoly.py`: explicit import/style/validation recipe.
- `../../scripts/build_safe_blender_run.py`: prepares allowed inline MCP code and data batches; direct external-module loading is not permitted by this connector's safe mode.
- Saved inline and resume scripts in this working directory record this run; they are bound to unique run filenames. Do not rerun them against existing datablocks/files. Use a new run identifier and checkpoint for a subsequent pass.

The generic dedicated recipe produces the initial palette; the final palette/attribution refinement is documented above and saved in the final .blend. Earlier styled versions and renders are retained for comparison. GIS remains authoritative. Further styling should continue with a new checkpoint and the same full baseline comparison; routing, verified entrances, measured heights and survey-grade alignment remain separate work.
