"""Offline saved-file landmark refinement; never connects to the live session.

Use Blender --background <validated saved blend> --python this_file -- inspect|apply|validate|render.
Host-prepared geometry uses explicit illustrative parameters and unchanged footprint envelopes.
"""
import ast
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
RUN = 'rpi_lowpoly_20261011_pass03_r02'
BASE = ROOT / 'blender/working/rpi_lowpoly_20261010_pass02_v03.blend'
OUT = ROOT / 'blender/working' / (RUN + '_v01.blend')
CHECKPOINT = ROOT / 'blender/checkpoints' / (RUN + '_before_changes.blend')
BASELINE = ROOT / 'blender/checkpoints' / (RUN + '_baseline.json.gz')
PAYLOAD = ROOT / 'blender/working' / (RUN + '_landmarks.json')
REPORT = ROOT / 'blender/working' / (RUN + '_validation.json')

# Reuse the real original validator's exact representation, not placeholder scripts.
source = (ROOT / 'blender/working/rpi_lowpoly_20261010_01_validate.py').read_text()
for node in ast.parse(source).body:
    if isinstance(node, ast.FunctionDef) and node.name in {'object_name', 'plain', 'props', 'object_state'}:
        exec(ast.get_source_segment(source, node))
source = (ROOT / 'scripts/blender_pass02.py').read_text()
for node in ast.parse(source).body:
    if isinstance(node, ast.FunctionDef) and node.name == 'original_validation':
        exec(ast.get_source_segment(source, node))

def normalized(x):
    return json.loads(json.dumps(x, sort_keys=True))

def state(obj):
    result = object_state(obj)
    result['materials'] = [m.name if m else None for m in obj.data.materials] if obj.data and hasattr(obj.data, 'materials') else []
    if obj.type == 'FONT':
        result['font'] = {'body': obj.data.body, 'size': obj.data.size}
    if obj.type == 'CURVE':
        result['world_spline_points'] = [[list(obj.matrix_world @ Vector(p.co[:3])) for p in s.points] for s in obj.data.splines]
    return normalized(result)

def collection_state(c):
    return {'children': sorted(x.name for x in c.children), 'objects': sorted(o.name for o in c.objects),
            'metadata': props(c), 'library': c.library.filepath if c.library else None}

def snapshot():
    bpy.context.view_layer.update()
    return normalized({'objects': {o.name: state(o) for o in sorted(bpy.data.objects, key=object_name)},
                       'collections': {c.name: collection_state(c) for c in bpy.data.collections},
                       'scene_metadata': props(bpy.context.scene)})

def write_new(path, data):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')

def inspect():
    report = original_validation()
    if not report['passed']:
        docs = json.loads(bpy.data.collections['RPI_AUDIT']['baseline_documents_json'])
        baseline = next(v for k,v in docs.items() if k.endswith('_source_baseline.json'))
        for name, old in baseline['objects'].items():
            now = normalized(object_state(bpy.data.objects[name]))
            for key in old:
                if old[key] != now[key]:
                    print(json.dumps({'object': name, 'field': key, 'before': old[key], 'now': now[key]}))
    assert report['passed'], report
    print(json.dumps({'saved_file_only': bpy.data.filepath, 'blender_version': bpy.app.version_string,
        'scene': bpy.context.scene.name, 'objects': len(bpy.data.objects), 'original_validation': report,
        'targets': [state(o) for o in bpy.data.collections['DISPLAY_BUILDINGS'].objects
                    if o.get('source_id') in ['osm/way/104737202','osm/way/104737275','osm/way/104737234','osm/way/104737313']]}, indent=2))

def material(name, color):
    m = bpy.data.materials.new(RUN + '_' + name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    node = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Roughness'].default_value = .85
    return m

def validate():
    with gzip.open(BASELINE, 'rt', encoding='utf-8') as f:
        before = json.load(f)
    payload = json.loads(PAYLOAD.read_text())
    hidden = {'VIS_' + key.replace('/', '_') for key, value in payload['buildings'].items() if value['replace_display']}
    errors = []
    for name, prior in before['objects'].items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            errors.append('Missing original object ' + name)
            continue
        current = state(obj)
        if name in hidden:
            if not current['hide_render'] or not current['hide_viewport']:
                errors.append('Replacement visibility ' + name)
            for field in ('hide_render', 'hide_viewport'):
                current[field] = prior[field]
        if current != prior:
            errors.append('Original object changed ' + name)
    for name, prior in before['collections'].items():
        c = bpy.data.collections.get(name)
        if c is None:
            errors.append('Missing collection ' + name)
            continue
        current = normalized(collection_state(c))
        if name == 'DISPLAY_NONAUTHORITATIVE':
            current['children'] = [n for n in current['children'] if n != RUN]
        if current != prior:
            errors.append('Original collection changed ' + name)
    if normalized(props(bpy.context.scene)) != before['scene_metadata']:
        errors.append('Scene geographic metadata changed')
    original = original_validation()
    errors.extend(original['errors'])
    maximum = 0.0
    count = 0
    for key, b in sorted(payload['buildings'].items()):
        for part in b['meshes']:
            obj = bpy.data.objects.get(RUN + '_' + part['name'])
            if obj is None:
                errors.append('Missing new mesh ' + part['name'])
                continue
            if len(obj.data.vertices) != len(part['vertices']):
                errors.append('New vertex count ' + part['name'])
                continue
            for v, expected in zip(obj.data.vertices, part['vertices']):
                world = obj.matrix_world @ v.co
                maximum = max(maximum, max(abs(world[i] - expected[i]) for i in range(3)))
            if [list(p.vertices) for p in obj.data.polygons] != part['faces']:
                errors.append('New topology ' + part['name'])
            if obj.get('source_id') != key or obj.get('height_status') != 'Illustrative, not measured':
                errors.append('New metadata ' + part['name'])
            count += 1
    if maximum > .0001:
        errors.append('New mesh serialization tolerance exceeded')
    result = {'passed': not errors, 'errors': errors, 'baseline_objects': len(before['objects']),
        'baseline_collections': len(before['collections']), 'original_source_validation': original,
        'original_geometry_topology_metadata_exact': not errors, 'new_meshes': count,
        'new_mesh_max_serialization_error_m': maximum, 'presentation_visibility_exceptions': sorted(hidden),
        'baseline_sha256': hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
        'payload_sha256': hashlib.sha256(PAYLOAD.read_bytes()).hexdigest(),
        'checks': ['All original object world/local transforms, world vertices, mesh edges/faces/loops',
                   'Original source metadata, ordered graph and multilevel tags',
                   'Nested collection hierarchy, linked object memberships and library references',
                   'Original curves including world-space points; original material assignments',
                   'New meshes match independently footprint-validated payload'],
        'limitations': ['New roof heights and part boundaries are illustrative; no measured heights inferred.',
                       'No routing, accessibility, pavement or source-coordinate correction.']}
    if REPORT.exists():
        assert json.loads(REPORT.read_text()) == result, 'Saved validation differs'
    else:
        write_new(REPORT, result)
    assert result['passed'], result
    print(json.dumps(result, indent=2))
    return result

def apply():
    assert Path(bpy.data.filepath).resolve() == BASE.resolve()
    for p in [OUT, CHECKPOINT, BASELINE, REPORT]:
        assert not p.exists(), 'Refusing overwrite: ' + str(p)
    assert original_validation()['passed']
    assert bpy.data.collections.get(RUN) is None
    data = json.loads(PAYLOAD.read_text())
    assert data['validation']['passed']
    before = snapshot()
    with BASELINE.open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
            stream.write(json.dumps(before, sort_keys=True, separators=(',', ':')).encode())
    bpy.ops.wm.save_as_mainfile(filepath=str(CHECKPOINT), copy=True)
    root = bpy.data.collections.new(RUN)
    bpy.data.collections['DISPLAY_NONAUTHORITATIVE'].children.link(root)
    root['role'] = 'Illustrative roof presentation only; no GIS updates'
    root['parameters_json'] = json.dumps(data['parameters'], sort_keys=True)
    palette = {'slate': (.16, .24, .26), 'cream': (.81, .76, .62),
               'light_roof': (.80, .81, .72), 'dark_roof': (.23, .29, .28),
               'brick': (.56, .29, .18), 'glass': (.17, .37, .40)}
    materials = {name: material(name, color) for name, color in palette.items()}
    for key, building in sorted(data['buildings'].items()):
        original = bpy.data.objects['VIS_' + key.replace('/', '_')]
        if building['replace_display']:
            original.hide_render = True
            original.hide_viewport = True
        for part in building['meshes']:
            name = RUN + '_' + part['name']
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(part['vertices'], [], part['faces'])
            mesh.update()
            obj = bpy.data.objects.new(name, mesh)
            root.objects.link(obj)
            mesh.materials.append(materials[part['material']])
            obj['source_id'] = key
            obj['height_status'] = 'Illustrative, not measured'
            obj['geometry_role'] = 'Presentation detail within unchanged source footprint; not routing geometry'
            obj['reference'] = building['reference']
            obj['crs'] = 'EPSG:26918'
            obj['origin_projected_m'] = data['origin_projected_m']
    # New detail cameras; the original overview and every old object stay unchanged.
    for label, keys in [('greene', ['osm/way/104737202']), ('jec_dcc', ['osm/way/104737275','osm/way/104737313']), ('union', ['osm/way/104737234'])]:
        vertices = [Vector(v) for key in keys for p in data['buildings'][key]['meshes'] for v in p['vertices']]
        lo = Vector(tuple(min(v[i] for v in vertices) for i in range(3)))
        hi = Vector(tuple(max(v[i] for v in vertices) for i in range(3)))
        target = (lo + hi) / 2
        camera = bpy.data.objects.new(RUN + '_camera_' + label, bpy.data.cameras.new(RUN + '_camera_' + label))
        root.objects.link(camera)
        camera.location = target + Vector((55, -120, 145))
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = max(hi.x-lo.x, hi.y-lo.y) * 1.5 + 18
        camera.data.clip_end = 10000
    bpy.context.view_layer.update()
    validate()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT))

def render():
    assert Path(bpy.data.filepath).resolve() == OUT.resolve()
    validate()
    scene = bpy.context.scene
    original_camera = scene.camera
    targets = [('overview', original_camera)] + [(name, bpy.data.objects[RUN + '_camera_' + name]) for name in ['greene','jec_dcc','union']]
    for name, camera in targets:
        path = ROOT / 'renders' / (RUN + '_' + name + '.png')
        assert not path.exists(), 'Refusing overwrite: ' + str(path)
        scene.camera = camera
        scene.render.filepath = str(path)
        scene.render.resolution_x = 2100 if name == 'overview' else 1400
        scene.render.resolution_y = 1500 if name == 'overview' else 1100
        scene.render.resolution_percentage = 100
        scene.cycles.samples = 40
        scene.cycles.seed = 0
        scene.cycles.use_animated_seed = False
        scene.cycles.use_denoising = True
        # Old annotations belong to the overview camera; hide only in transient detail renders.
        annotation_col = bpy.data.collections['rpi_lowpoly_20261010_pass02_ANNOTATIONS']
        annotation_col.hide_render = name != 'overview'
        bpy.ops.render.render(write_still=True)
    # Render settings are transient; do not save over the validated scene.

if __name__ == '__main__':
    # Saved files can contain inactive scenes whose transform caches start at identity.
    # Evaluate every view layer before reading matrices; no transform assignments.
    for scene in bpy.data.scenes:
        for view_layer in scene.view_layers:
            with bpy.context.temp_override(scene=scene, view_layer=view_layer):
                view_layer.update()
    mode = sys.argv[sys.argv.index('--') + 1]
    {'inspect': inspect, 'apply': apply, 'validate': validate, 'render': render}[mode]()
