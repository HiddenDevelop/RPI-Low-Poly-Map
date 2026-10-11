"""Build deterministic illustrative roof parts inside unchanged pilot footprints.

Imagery coordinates below identify visual regions, not measured building-part GIS.
All Z adjustments are explicit presentation parameters. No GIS output is modified.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from pyproj import datadir, network
from pyproj.transformer import TransformerGroup
from shapely import affinity, constrained_delaunay_triangles
from shapely.geometry import Polygon, box, mapping
from shapely.geometry.polygon import orient
from shapely.ops import transform, triangulate, unary_union

ROOT = Path(__file__).resolve().parents[1]
RUN = 'rpi_lowpoly_20261011_pass03_r02'
EVIDENCE = ROOT / 'gis/cleaned/evidence_20261010_01'

def pieces(g):
    if g.geom_type == 'Polygon':
        return [g] if g.area > 1e-8 else []
    return [p for child in getattr(g, 'geoms', []) for p in pieces(child)]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'blender/working' / (RUN + '_landmarks.json'))
    out = parser.parse_args().out
    payload_path = ROOT / 'blender/working/rpi_lowpoly_20261010_01_payload.json'
    source = json.loads(payload_path.read_text())
    origin = source['origin_projected_m']
    network.set_network_enabled(False)
    datadir.append_data_dir(str(ROOT / 'gis/acquisitions/evidence_20261010_01/source/datum'))
    group = TransformerGroup(6537, 26918, always_xy=True, allow_ballpark=False)
    assert group.best_available and group.transformers
    t = group.transformers[0]
    def from_native(polygon):
        return affinity.translate(transform(t.transform, polygon), -origin[0], -origin[1])
    targets = {'osm/way/104737202': 'Greene', 'osm/way/104737275': 'JEC',
               'osm/way/104737234': 'Union', 'osm/way/104737313': 'DCC'}
    parameters = {'greene_hip_rise_m': 5.0, 'greene_roof_windows_per_long_side': 4,
                  'jec_north_delta_m': 2.5, 'jec_south_delta_m': -5.0,
                  'union_main_delta_m': 0.0, 'union_annex_delta_m': -3.5,
                  'dcc_main_delta_m': 0.0, 'dcc_north_delta_m': 2.5,
                  'parapet_width_m': .32, 'parapet_height_m': .45,
                  'status': 'All dimensions and internal part boundaries are illustrative, not surveyed.'}
    output = {}
    partition_checks = {}
    for item in sorted(source['features'], key=lambda d: d['feature']['id']):
        f = item['feature']
        key = f['id']
        if key not in targets:
            continue
        name = targets[key]
        assert f['geometry']['type'] == 'Polygon' and len(f['geometry']['coordinates']) == 1
        footprint = affinity.translate(Polygon(f['geometry']['coordinates'][0]), -origin[0], -origin[1])
        roof = max(item['ground_center'] + item['display_height_m'], max(item['ground_samples']) + 4)
        base = item['ground_base']
        meshes = []
        def surface(label, polygon, height, material):
            for i, poly in enumerate(pieces(polygon)):
                vertices, faces = [], []
                triangles = []
                for tri in constrained_delaunay_triangles(poly).geoms:
                    ring = list(orient(tri, sign=1).exterior.coords)[:-1]
                    triangles.append(tri)
                    start = len(vertices)
                    vertices.extend([[x, y, height(x, y)] for x, y in ring])
                    faces.append([start, start+1, start+2])
                assert faces, label
                assert poly.symmetric_difference(unary_union(triangles)).area < 1e-6, 'Incomplete triangulation: ' + label
                meshes.append({'name': name + '_' + label + '_' + str(i), 'vertices': vertices, 'faces': faces, 'material': material})
        def walls(label, polygon, bottom, top, material):
            vertices, faces = [], []
            for poly in pieces(polygon):
                poly = orient(poly, sign=1)
                for ring in [poly.exterior, *poly.interiors]:
                    for a, b in zip(ring.coords, list(ring.coords)[1:]):
                        start = len(vertices)
                        vertices.extend([[*a, bottom], [*b, bottom], [*b, top], [*a, top]])
                        faces.append([start,start+1,start+2,start+3])
            meshes.append({'name': name + '_' + label, 'vertices': vertices, 'faces': faces, 'material': material})
        def mass(label, polygon, top, roof_material):
            walls(label + '_walls', polygon, base, top, 'cream')
            surface(label + '_roof', polygon, lambda x,y: top, roof_material)
            rim = polygon.difference(polygon.buffer(-parameters['parapet_width_m'], join_style=2))
            surface(label + '_parapet', rim, lambda x,y: top + parameters['parapet_height_m'], 'cream')
            walls(label + '_rim', rim, top, top + parameters['parapet_height_m'], 'cream')
        parts = []
        if name == 'Greene':
            rect = list(footprint.minimum_rotated_rectangle.exterior.coords)
            _, a, b = max((math.dist(a,b), a,b) for a,b in zip(rect,rect[1:]))
            angle = math.atan2(b[1]-a[1], b[0]-a[0])
            local = affinity.rotate(footprint, -angle, origin=(0,0), use_radians=True)
            xmin,ymin,xmax,ymax = local.bounds
            mid = (ymin+ymax)/2
            half = (ymax-ymin)/2
            left, right = (xmin+half, mid), (xmax-half, mid)
            facets = [Polygon([(xmin,ymin),(xmax,ymin),right,left]),
                      Polygon([(xmax,ymin),(xmax,ymax),right]),
                      Polygon([(xmax,ymax),(xmin,ymax),left,right]),
                      Polygon([(xmin,ymax),(xmin,ymin),left])]
            def world(g):
                return affinity.rotate(g, angle, origin=(0,0), use_radians=True)
            def height(x,y):
                u = x*math.cos(angle)+y*math.sin(angle)
                v = -x*math.sin(angle)+y*math.cos(angle)
                rise = min(u-xmin,xmax-u,v-ymin,ymax-v) / half
                return roof + .08 + max(0, rise)*parameters['greene_hip_rise_m']
            for i, facet in enumerate(facets):
                part = world(local.intersection(facet))
                parts.append(part)
                surface('hip_' + str(i), part, height, 'slate')
            # Small raised window cues follow the roof slope; dormer geometry remains unverified.
            for side in [0,1]:
                for i in range(4):
                    u = xmin + (xmax-xmin)*(.2+.2*i)
                    v = ymin+(ymax-ymin)*(.24 if side == 0 else .76)
                    frame = world(box(u-1.3,v-1.0,u+1.3,v+1.0)).intersection(footprint)
                    pane = world(box(u-1.02,v-.76,u+1.02,v+.76)).intersection(footprint)
                    surface(f'roof_window_frame_{side}_{i}', frame, lambda x,y: height(x,y)+.12, 'cream')
                    surface(f'roof_window_pane_{side}_{i}', pane, lambda x,y: height(x,y)+.17, 'glass')
            replace = False
        else:
            if name == 'JEC':
                north = from_native(Polygon([(711000,1420582),(714000,1420222),(714000,1423000),(711000,1423000)]))
                first = footprint.intersection(north)
                second = footprint.difference(north)
                specs = [('north',first,roof+parameters['jec_north_delta_m'],'light_roof'),
                         ('south',second,roof+parameters['jec_south_delta_m'],'dark_roof')]
            elif name == 'Union':
                main = from_native(Polygon([(713230,1420707),(713433,1420672),(713405,1420530),(713204,1420565)]))
                first = footprint.intersection(main)
                second = footprint.difference(main)
                specs = [('main',first,roof,'dark_roof'), ('annex',second,roof+parameters['union_annex_delta_m'],'light_roof')]
            else:
                north = from_native(Polygon([(711000,1420675),(714000,1420315),(714000,1423000),(711000,1423000)]))
                first = footprint.intersection(north)
                second = footprint.difference(north)
                specs = [('north',first,roof+parameters['dcc_north_delta_m'],'dark_roof'), ('hall',second,roof,'light_roof')]
            for label, region, top, color in specs:
                assert region.area > 1 and top > base
                parts.append(region)
                mass(label, region, top, color)
            replace = True
        union = unary_union(parts)
        difference = footprint.symmetric_difference(union).area
        overlap = sum(p.area for p in parts)-union.area
        assert difference < 1e-6 and abs(overlap) < 1e-6, (name, difference, overlap)
        max_outside = 0.0
        for mesh in meshes:
            assert all(math.isfinite(n) for v in mesh['vertices'] for n in v)
            for face in mesh['faces']:
                xy = [mesh['vertices'][i][:2] for i in face]
                if len(set(tuple(p) for p in xy)) < 3:
                    continue
                projected = Polygon(xy)
                max_outside = max(max_outside, projected.difference(footprint).area)
        assert max_outside < 1e-6
        partition_checks[key] = {'symmetric_difference_m2': difference, 'overlap_m2': overlap,
                                'max_face_outside_footprint_m2': max_outside}
        output[key] = {'name': name, 'source_id': key, 'source_geometry': f['geometry'],
            'source_feature_sha256': hashlib.sha256(json.dumps(f,sort_keys=True).encode()).hexdigest(),
            'footprint_local': mapping(footprint), 'replace_display': replace, 'meshes': meshes,
            'original_roof_z_m': roof, 'base_z_m': base,
            'reference': 'gis/cleaned/evidence_20261010_01/' + key.replace('/','_') + '_review.png',
            'roof_parts_local': [mapping(p) for p in parts]}
    result = {'run': RUN, 'crs': 'EPSG:26918', 'units': 'metres', 'origin_projected_m': origin,
        'parameters': parameters, 'buildings': output,
        'reference_date': '2026-10-11',
        'reference_scope': '2024 NYS aerial imagery for visual forms; RPI archives for identity/history. No imported textures.',
        'datum_operation': {'pipeline': t.definition, 'accuracy_m': t.accuracy},
        'evidence_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(EVIDENCE.glob('*_review.png'))},
        'validation': {'passed': True, 'buildings': len(output), 'footprint_part_checks': partition_checks,
                       'no_source_changes': True, 'accessibility_inferred': False},
        'limitations': ['Roof-window cues do not establish dormer geometry or count.',
                       'Internal roof-region boundaries are visual approximations, clipped to existing footprints.',
                       'All roof heights remain illustrative; no vertical datum measurements added.']}
    with out.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    print(json.dumps({'out': str(out), 'validation': result['validation']}))

if __name__ == '__main__':
    main()
