# Pass 03: landmark roof forms

Date: 2026-10-11. Branch: `codex/pilot-landmark-roofs-pass03`.

Working model: [rpi_lowpoly_20261011_pass03_r02_v01.blend](rpi_lowpoly_20261011_pass03_r02_v01.blend).

## Changes

Four buildings received 44 new presentation meshes, with flat materials and simplified silhouettes:

- Greene: four hip-roof facets and eight small roof-window cues. Roof rise is an illustrative 5 m. Aerial evidence supports the hip form and roof openings, but does not verify dormer construction, exact count or dimensions; these are deliberately described as window cues.
- JEC: separate northern and southern roof masses, with illustrative offsets of +2.5 m and -5 m from the former display roof, plus thin parapets.
- Union: main roof and a lower surrounding/annex mass, with an illustrative 3.5 m difference. The curved southern footprint is retained.
- DCC: long pale hall roof and a darker northern wing, with an illustrative 2.5 m difference.

Existing height estimates remain the reference, not measured elevations. Three original display extrusions are retained and hidden in rendering/viewport; their transforms, mesh coordinates, topology and metadata are unchanged. Greene's original display extrusion remains visible under its new roof. All source footprints, roads, paths, accessibility nodes and terrain are unchanged. No new doors, curb cuts, routes or accessibility values were inferred.

## References and uncertainty

The [sealed 2024 NYS imagery review](../../gis/cleaned/evidence_20261010_01/README.md) supplies the visual roof-region evidence. Paired panels are identified by source ID in the [landmark payload](rpi_lowpoly_20261011_pass03_r02_landmarks.json), together with SHA-256 hashes. Imagery was reviewed, not used as a photorealistic texture.

Official RPI identity/history references reviewed on 2026-10-11:

- [Greene Building](https://archives.rpi.edu/institute-history/building-histories/greene-building)
- [Jonsson Engineering Center](https://archives.rpi.edu/institute-history/building-histories/jonsson-engineering-center)
- [Darrin Communication Center](https://archives.rpi.edu/institute-history/building-histories/darrin-communication-center)

These historical pages do not establish current roof dimensions. No photographs were copied into this project. Source attribution/license notes remain in the evidence review; original geometry retains OSM provenance. New procedural presentation meshes are project output, not new authoritative GIS.

Roof-region boundaries were visually approximated in the imagery's EPSG:6537 coordinates, transformed with the archived NADCON5 grids to EPSG:26918, and clipped to the unchanged source footprints. The operation is recorded in the payload. One Blender unit is one metre; the existing origin `[608100, 4731600, 0]` remains unchanged. No new vertical datum operation was performed. Roof Z adjustments are illustrative, and the previous source-position uncertainty remains.

## Safeguards and validation

The live Blender MCP could not connect. Work therefore used a separate Blender 5.2.2 process with `--factory-startup`, reading only the saved pass-02 model. The open interactive session was not edited. No add-on settings, services, firewall rules or sockets were changed.

A unique [checkpoint](../checkpoints/rpi_lowpoly_20261011_pass03_r02_before_changes.blend) and [complete baseline](../checkpoints/rpi_lowpoly_20261011_pass03_r02_baseline.json.gz) were saved before edits. Inactive scenes require view-layer evaluation before reading cached transforms; evaluating them resolved identity-matrix caches for the unrelated default Camera/Light without modifying their transforms.

[Validation report](rpi_lowpoly_20261011_pass03_r02_validation.json):

- All 1,210 original objects and 20 original collections were compared, including world/local transforms, world-space mesh vertices, edges/faces/loops, metadata, original curves, materials, nested collections and linked memberships.
- The original 455-object source baseline and embedded ordered graph still pass.
- The only original-object exceptions are render/viewport visibility on the three retained presentation extrusions; no geometry or metadata exceptions are allowed.
- New mesh vertices/faces match the independently generated payload, with maximum Blender float serialization difference under 0.0001 m. This tolerance is not a source movement tolerance: original geometry compares exactly.
- Roof-part unions equal the original footprints within numerical roundoff (maximum symmetric-difference area below 1e-12 square metres). Constrained triangulation is checked for complete coverage, including holes and concave boundaries.
- The original GIS validator passes: 47 sealed raw files, 4,108 graph elements, 4,488 segments, 78 boundary crossings and 27 separate NYS footprints. Unknown accessibility and multilevel tags remain intact. Placeholder importer and scene-validator files remain untouched.
- Rebuilding the final landmark payload produced identical SHA-256 `2b2103144f8e98d99f1071ab0c0f2586ffe0c24fc7a6fad0fbd47c3a6814815a`.

An earlier draft was rejected by the roof triangulation coverage check. It is retained locally under `.local/pass03_superseded/`; only the corrected `r02` scene is the deliverable.

## Review images and reproduction

[Overview](../../renders/rpi_lowpoly_20261011_pass03_r02_overview.png) · [Greene](../../renders/rpi_lowpoly_20261011_pass03_r02_greene.png) · [JEC/DCC](../../renders/rpi_lowpoly_20261011_pass03_r02_jec_dcc.png) · [Union](../../renders/rpi_lowpoly_20261011_pass03_r02_union.png)

The overview keeps the prior camera and labels for comparison. Close-ups use three new cameras; temporary render settings are not saved over the validated model. Renders use Cycles, 40 samples, denoising and seed 0. These are visualizations, not accessibility maps certified for navigation.

Use the pinned GIS dependencies from the evidence package. `scripts/prepare_pass03_landmarks.py --out <new-path>` reproduces the payload without changing sources. Run the saved-scene validator with:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup blender/working/rpi_lowpoly_20261011_pass03_r02_v01.blend --python-exit-code 1 --python scripts/blender_pass03.py -- validate
```

Apply and render refuse existing artifact names. A future pass must use a new run ID. Pavement corrections, measured building heights and current accessibility verification remain separate next steps.
