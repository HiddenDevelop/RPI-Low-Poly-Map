# Finish the local Blender connection

## Why activation is manual

The add-on opens an unauthenticated TCP socket that can run Python inside Blender. Safe mode checks scripts sent through the MCP server, but does not authenticate the socket, enforce protected file paths, or confine all bpy operations. Treat local applications and Blender files as trusted inputs. Stop if Windows requests elevation or firewall access; no firewall exception or public network exposure is required.

The prepared add-on differs from upstream in two reviewed defaults: listener host is explicitly 127.0.0.1 and automatic startup is off. Telemetry consent and all optional external integrations default off upstream. Do not use the upstream one-command installer or automatic updater: it can replace this prepared copy and its defaults.

## Manual actions

1. Open Blender 5.2.2 LTS yourself. If you open an existing project, save unsaved work safely before enabling third-party tools. Do not load or overwrite a master file for testing.
2. In Edit > Preferences > Add-ons, use the menu's Install from Disk action and select `C:/Users/TheMa/Documents/Codex/2026-10-09/i-am-building-a-disability-accessible/outputs/rpi-access-map/setup/blender_mcp.py`. Enable MCP for Blender. If an add-on with this name already exists, stop rather than overwrite it; review and back up that installation first.
3. In add-on preferences, leave Allow Telemetry off. Leave asset/generation integrations off. Do not enable automatic Python execution in Blender preferences.
4. In the 3D viewport, press N and choose MCP for Blender. Leave Auto-Start Server off, set port 9876, then click Start MCP Server (the label may say Connect). Stop the server when finished.
5. Open this folder as a project in Codex. Review its AGENTS.md and `.codex/config.toml`, and trust the folder only if you approve the contents. Reload the MCP connection or restart Codex to load the new tools. This existing chat will not necessarily gain new tools immediately.
6. In a normal PowerShell terminal:

```powershell
Set-Location -LiteralPath 'C:\Users\TheMa\Documents\Codex\2026-10-09\i-am-building-a-disability-accessible\outputs\rpi-access-map'
codex mcp get blender
codex mcp list
Get-NetTCPConnection -LocalPort 9876 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
```

The listener must be 127.0.0.1 (or loopback ::1 for a different implementation). Stop if it is 0.0.0.0, ::, a LAN address, or an unexpected process. MCP list/get verify registration, not a working scene connection. In CLI, /mcp shows connected servers.

## First live verification

Ask Codex: "Use the Blender MCP read-only first. Report the current blend filepath, scene names, all collections including nested collections, mesh objects, lights, and cameras. Do not change selection, mode, geometry, materials, or files. Confirm loopback binding and telemetry off."

get_scene_info may truncate or only show top-level objects. Use a read-only execute_blender_code query of bpy.data.collections and bpy.data.objects to complete the inventory; paginate if needed.

Only after successful inspection, ask: "Create one temporary MCP_TEST cube using the data API. Abort if that name already exists or the scene is in Edit mode. Compute a location beyond the world-space bounding boxes of all existing scene objects, accounting for instances. Verify the exact object and mesh references, then delete only those newly created datablocks in a finally block. Preserve existing selection, mode, objects, collections, and transforms. Do not save the blend file. Verify MCP_TEST is absent and the existing scene geometry and metadata match the baseline."

If placement or cleanup cannot be verified, stop and report it. A temporary cube can mark the session as changed even after removal; do not save automatically. No cube test has been performed during setup because no live Blender process was available.

## Rebuilding the local MCP environment

The current .venv is already installed. Do not run these commands unless rebuilding into a new environment is intended. Source revision and add-on hashes are in upstream.json. dependencies are recorded in requirements-lock.txt. Keep the patched add-on; do not replace it with the bundled upstream add-on.

Clone the upstream repository into a fresh local directory, checkout the exact commit in upstream.json, create a project-local venv using the installed Python, install requirements-lock.txt, then install that local source with --no-deps. Update .codex/config.toml only if the project is moved. No package manager or administrator installation is needed.

## Rollback

Stop the Blender MCP server and disable the add-on through Blender preferences. Disable the project MCP entry or remove its table from the project-local config. Do not delete other Codex server configurations. Keep source GIS and .blend files. No global security settings need undoing.
