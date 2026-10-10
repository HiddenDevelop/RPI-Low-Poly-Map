# Project purpose

Create a geographically accurate, low-poly RPI campus map for disability-accessible pathfinding.

## Geographic integrity

- Never alter the XY positions of sidewalks, roads, ramps, entrances, stairs, elevators, accessibility nodes, or building footprints unless the user explicitly requests it.
- Never modify files inside `gis/raw/`.
- Preserve accessibility metadata.
- Record source, license, acquisition date, coordinate reference system, units, and any local origin offset. Preserve uncertainty and unknown accessibility values.

## Blender safety

- Never overwrite files inside `blender/master/`.
- Work in `blender/working/`.
- Save checkpoints before major scene modifications.
- Do not make destructive changes without a recoverable checkpoint.
- Use new, unique filenames; never silently overwrite a working file or checkpoint.

## Protected Blender collections

- `TERRAIN_LOCKED`
- `PATHS_LOCKED`
- `ACCESSIBILITY_LOCKED`
- `ENTRANCES_LOCKED`

## Visual style

- cute low-poly
- simple silhouettes
- flat or lightly shaded materials
- warm campus palette
- simplified roofs
- simplified vegetation
- no photorealistic textures

## Workflow

- Prefer Python scripts for imports and procedural generation.
- Use deterministic inputs, explicit parameters, sorted processing, and fixed random seeds.
- Use live Blender MCP mainly for inspection, testing, and visual refinement.
- Inspect the open scene without changes before any live editing.
- After substantial Blender changes, render an overview image for review.
- Report what changed.
- Validate that protected geometry was not moved: compare object world transforms and world-space vertex coordinates against a saved baseline, including nested collections and linked objects. Check metadata and topology too. A placeholder validator is not evidence of a passing validation.
- Keep the Blender socket on loopback only. Do not change firewall rules, expose ports, enable telemetry, or enable external asset/generation services without explicit authorization.
- Do not import GIS data until provenance, CRS, units, origin, and accessibility schema have been reviewed.
