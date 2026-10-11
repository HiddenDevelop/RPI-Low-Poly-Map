"""Deterministic evidence-only LiDAR inspection and source-linked review items.

No corrected geometry, routing attributes, or scene modifications are generated.
Outputs must not already exist. Run in the isolated GIS environment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import laspy
import numpy as np
from pyproj import datadir, network
from pyproj.transformer import TransformerGroup
from shapely import contains_xy
from shapely.geometry import shape, mapping, box
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'gis/acquisitions/evidence_20261010_01/source'
REVIEW = ROOT / 'gis/cleaned/evidence_20261010_01'

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, data):
    with p.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=REVIEW)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    network.set_network_enabled(False)
    datadir.append_data_dir(str(SOURCE / 'datum'))
    group = TransformerGroup(26918, 6350, always_xy=True, allow_ballpark=False)
    assert group.best_available and group.transformers
    operation = group.transformers[0]
    buildings = read(ROOT / 'gis/cleaned/pilot/osm/buildings.json')['features']
    geometries = {f['id']: transform(operation.transform, shape(f['geometry'])) for f in buildings}
    study = transform(operation.transform, shape(read(REVIEW / 'imagery_review.json')['comparison_aoi_26918']))
    tiles = []
    for p in sorted((SOURCE / 'elevation').glob('*.laz')):
        cloud = laspy.read(p)
        crs = cloud.header.parse_crs()
        assert crs.sub_crs_list[0].to_epsg() == 6350
        assert crs.sub_crs_list[1].to_epsg() == 5703
        x, y, z = np.asarray(cloud.x), np.asarray(cloud.y), np.asarray(cloud.z)
        classification = np.asarray(cloud.classification)
        eligible = (~np.asarray(cloud.withheld, dtype=bool) & ~np.asarray(cloud.overlap, dtype=bool)
                    & np.isfinite(x) & np.isfinite(y) & np.isfinite(z))
        inside = eligible & contains_xy(study, x, y)
        codes, counts = np.unique(classification[inside], return_counts=True)
        samples = []
        for key, polygon in sorted(geometries.items()):
            mask = eligible & (classification == 6) & contains_xy(polygon, x, y)
            values = z[mask]
            samples.append({'source_id': key, 'classified_building_returns': int(len(values)),
                            'z_navd88_m_p10_p50_p95': np.percentile(values, [10, 50, 95]).tolist() if len(values) else None})
        tiles.append({'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p),
                      'crs_wkt': crs.to_wkt(), 'point_count': cloud.header.point_count,
                      'bounds_xyz': [cloud.header.mins.tolist(), cloud.header.maxs.tolist()],
                      'eligible_aoi_returns': int(inside.sum()),
                      'aoi_class_counts': dict(zip(map(str, codes), map(int, counts))),
                      'building_samples': samples})
        print(p.name, int(inside.sum()), 'eligible AOI returns', flush=True)
    assert len(tiles) == 2
    coverage = unary_union([box(t['bounds_xyz'][0][0], t['bounds_xyz'][0][1],
                               t['bounds_xyz'][1][0], t['bounds_xyz'][1][1]) for t in tiles])
    write(out / 'elevation_review.json', {
        'tiles': tiles, 'horizontal_epsg': 6350, 'vertical_epsg': 5703,
        'vertical_units': 'metres', 'geoid_model': 'GEOID12B',
        'capture_period': '2019-04-25 through 2020-09-25 (project metadata)',
        'project_metadata': 'source/elevation/fema_block4_pointcloud.xml',
        'tile_bbox_aoi_coverage_fraction': study.intersection(coverage).area / study.area,
        'operation': {'description': operation.description, 'pipeline': operation.definition,
                      'accuracy_m': operation.accuracy, 'projjson': operation.to_json_dict()},
        'limitations': ['Only horizontal coordinates transformed. Z remains native NAVD88/GEOID12B metres.',
                       'Tile bounding-box coverage is not proof of continuous classified-return coverage.',
                       'Class 6 samples are elevations, not building heights; no ground subtraction or model update.',
                       'Per-tile statistics stay separate; no merging or duplicate counting across tiles.',
                       'Withheld and overlap-flagged returns excluded. Unknown roof elevations remain null.',
                       '10 cm RMSEz is a project design class, not measured campus accuracy.',
                       'Temporal differences and inherited OSM datum uncertainty affect footprint sampling.']})
    observations = {
        '104737293': ('Folsom Library', 'Visible roof edges differ from the source outline; roof overhang, relief displacement and datum uncertainty must be resolved before any footprint correction.'),
        '104737275': ('Jonsson Engineering Center', 'Distinct roof regions and courtyard massing are missing from the uniform-height presentation.'),
        '104737234': ('Rensselaer Union', 'Main roof and lower extension need separate massing review; imagery alone does not establish heights.'),
        '104737202': ('Greene Building', 'Hipped roof and dormer forms are visible; simplified roof details would improve recognition.'),
        '104737313': ('Darrin Communications Center', 'Long roof and adjoining wing require separate massing review; courtyard shadows limit pavement interpretation.')}
    items = []
    by_id = {f['id']: f for f in buildings}
    for osm_id, (name, observation) in sorted(observations.items()):
        source_id = 'osm/way/' + osm_id
        items.append({'id': 'review/building/' + osm_id, 'name': name,
                      'status': 'candidate_requires_review', 'kind': 'building_massing_or_outline',
                      'observation': observation, 'source_ids': [source_id],
                      'geometry': by_id[source_id]['geometry'], 'geometry_role': 'unchanged complete source footprint',
                      'source_feature': by_id[source_id],
                      'reference': 'osm_way_' + osm_id + '_review.png',
                      'next_evidence': 'Ground-level or official architectural reference; inspect classified LiDAR elevations without assuming roof equals footprint.',
                      'accessibility_conclusion': None})
    layers = {name: read(ROOT / f'gis/cleaned/pilot/osm/{name}.json')['features'] for name in ['paths', 'roads', 'stairs']}
    native = TransformerGroup(6537, 26918, always_xy=True, allow_ballpark=False)
    assert native.best_available and native.transformers
    for name, bounds, note in [
        ('folsom_vcc_plaza', [711750, 1420250, 712000, 1420420], 'Broad paved spaces need area/width evidence beyond displayed centerlines.'),
        ('jec_dcc_courtyard', [712440, 1420300, 712600, 1420520], 'Trees and shadow obscure connections; do not infer missing links or accessibility.'),
        ('union_approaches', [713200, 1420450, 713450, 1420730], 'Approach widths and terraces vary; inspect pavement edges and grade changes before replacing display-width defaults.')]:
        roi = transform(native.transformers[0].transform, box(*bounds))
        linked = {f['id']: f for fs in layers.values() for f in fs if shape(f['geometry']).intersects(roi)}
        items.append({'id': 'review/pavement/' + name, 'kind': 'pavement_evidence_gap',
                      'status': 'candidate_requires_review', 'observation': note,
                      'geometry': mapping(roi), 'geometry_role': 'review window only; not a pavement polygon or route',
                      'source_ids': sorted(linked), 'source_features': [linked[k] for k in sorted(linked)],
                      'reference': 'source_overlay.png', 'accessibility_conclusion': None,
                      'next_evidence': 'Survey or ground-level verification for clear width, curb cuts, steps, slopes and entrances.'})
    write(out / 'discrepancy_review.json', {'schema': 'rpi-evidence-review-v1', 'crs': 'EPSG:26918',
          'units': 'metres', 'origin_offset': [0, 0, 0], 'features': items,
          'policy': 'Review annotations only; no source geometry, topology or accessibility changes. NYS remains separate.'})
    for item in items:
        originals = [item['source_feature']] if 'source_feature' in item else item['source_features']
        assert sorted(f['id'] for f in originals) == sorted(item['source_ids'])
        for feature in originals:
            candidates = buildings if feature['id'] in by_id else sum(layers.values(), [])
            assert feature == next(f for f in candidates if f['id'] == feature['id'])
    write(out / 'review_validation.json', {'passed': True, 'review_items': len(items),
          'complete_source_features_preserved': True, 'geometry_corrections': 0,
          'accessibility_assertions': 0, 'lidar_tiles': len(tiles),
          'note': 'Evidence-layer validation only. No Blender scene validation claimed.'})

if __name__ == '__main__':
    main()
