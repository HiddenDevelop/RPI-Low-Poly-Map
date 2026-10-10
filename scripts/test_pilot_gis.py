"""Regression and adversarial checks using copies in memory, never raw writes.

Run: .local/gis-venv/Scripts/python.exe -m unittest discover -s scripts -p test_pilot_gis.py -v
"""
import copy
import hashlib
import unittest
from pathlib import Path
from pilot_gis import ROOT,encoded,read,assemble_rings,osm_geometries
from prepare_pilot_gis import build
from validate_pilot_gis import validate_values

class PilotValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files={p.relative_to(ROOT/'gis/cleaned/pilot').as_posix():read(p)
                   for p in (ROOT/'gis/cleaned/pilot').rglob('*.json')}

    def rejected(self,edit):
        data=copy.deepcopy(self.files)
        edit(data)
        # Reseal the changed payload so tests exercise semantic validation,
        # not merely checksum detection.
        data['manifest.json']['file_sha256']={name:hashlib.sha256(encoded(data[name])).hexdigest()
                                            for name in data['manifest.json']['file_sha256']}
        report=validate_values(data)
        self.assertFalse(report['passed'],report)
        return report['error']

    def test_real_inventory_and_bitwise_repeatability(self):
        report=validate_values(self.files)
        self.assertTrue(report['passed'],report)
        self.assertEqual(report['source_graph_elements'],4108)
        self.assertEqual(report['source_way_segments'],4488)
        self.assertEqual(report['boundary_review_count'],78)
        rebuilt=build()
        for name,value in rebuilt.items():
            self.assertEqual(encoded(value),(ROOT/'gis/cleaned/pilot'/name).read_bytes(),name)

    def test_changed_path_coordinate_rejected(self):
        def edit(d): d['osm/paths.json']['features'][0]['geometry']['coordinates'][0][0]+=0.1
        self.assertIn('coordinate shift',self.rejected(edit))

    def test_missing_path_rejected(self):
        self.assertIn('feature IDs',self.rejected(lambda d:d['osm/paths.json']['features'].pop()))

    def test_duplicate_building_id_rejected(self):
        def edit(d): d['osm/buildings.json']['features'].append(copy.deepcopy(d['osm/buildings.json']['features'][0]))
        self.assertIn('feature IDs',self.rejected(edit))

    def test_dropped_outside_dependency_rejected(self):
        def edit(d):
            a=d['osm/source_graph.json']['elements']
            a.remove(next(e for e in a if e['scope']=='outside_dependency'))
        self.assertIn('graph elements',self.rejected(edit))

    def test_changed_relation_member_role_rejected(self):
        def edit(d):
            r=next(r for r in d['osm/source_graph.json']['elements'] if r['id']=='osm/relation/9312043')
            r['source']['members'][0]['role']='invented'
        self.assertIn('ordered members changed',self.rejected(edit))

    def test_removed_repeated_route_member_rejected(self):
        def edit(d):
            r=next(r for r in d['osm/source_graph.json']['elements'] if r['id']=='osm/relation/9312043')
            members=r['source']['members']; seen=[]
            for i,m in enumerate(members):
                if m in seen: members.pop(i); return
                seen.append(m)
            self.fail('Fixture has no repeated member')
        self.assertIn('ordered members changed',self.rejected(edit))

    def test_level_string_not_normalized(self):
        def edit(d):
            f=next(f for f in d['osm/paths.json']['features'] if 'level' in f['semantics'])
            f['semantics']['level']='0;1;2'
        self.assertIn('semantics changed',self.rejected(edit))

    def test_missing_accessibility_not_filled(self):
        def edit(d):
            f=next(f for f in d['osm/paths.json']['features'] if 'wheelchair' not in f['semantics'])
            f['semantics']['wheelchair']='yes'
        self.assertIn('semantics changed',self.rejected(edit))

    def test_native_nys_z_preserved(self):
        def edit(d): d['nys/buildings.json']['features'][0]['source']['geometry']['rings'][0][0][2]+=1
        self.assertIn('NYS native coordinates',self.rejected(edit))

    def test_boundary_review_complete(self):
        self.assertIn('Boundary-crossing',self.rejected(lambda d:d['boundary_review.json']['features'].pop()))

    def test_datum_accuracy_not_overstated(self):
        def edit(d): d['datum_operations.json']['stated_operation_accuracy_m']=0
        self.assertIn('Datum uncertainty',self.rejected(edit))

    def test_wrong_crs_rejected(self):
        def edit(d): d['osm/buildings.json']['crs']='EPSG:4326'
        self.assertIn('CRS',self.rejected(edit))

    def test_graph_segments_not_reordered(self):
        def edit(d): d['osm/source_graph.json']['way_segments'].reverse()
        self.assertIn('way segments/topology',self.rejected(edit))

    def test_changed_ring_node_provenance_rejected(self):
        def edit(d):
            r=next(r for r in d['osm/source_graph.json']['elements'] if r['id']=='osm/relation/6249058')
            r['assembled_ring_provenance']['outer'][0]['node_ids'][1]=123
        self.assertIn('ring node sequence',self.rejected(edit))

class ConservativeParserTests(unittest.TestCase):
    def test_endpoint_ids_join_without_changing_member_source(self):
        index={('way',1):{'nodes':[1,2,3]},('way',2):{'nodes':[1,4,3]}}
        before=copy.deepcopy(index)
        rings=assemble_rings([(0,{'type':'way','ref':1}),(1,{'type':'way','ref':2})],index)
        self.assertEqual(rings[0]['node_ids'],[1,2,3,4,1])
        self.assertTrue(rings[0]['pieces'][1]['reversed'])
        self.assertEqual(index,before)

    def test_distinct_endpoint_ids_never_snap(self):
        index={('way',1):{'nodes':[1,2]},('way',2):{'nodes':[3,1]}}
        with self.assertRaisesRegex(ValueError,'Unclosed'):
            assemble_rings([(0,{'type':'way','ref':1}),(1,{'type':'way','ref':2})],index)

    def test_zero_length_path_fails_without_repair(self):
        elements=[{'type':'way','id':1,'nodes':[1,2],'tags':{'highway':'footway'}}]
        with self.assertRaisesRegex(ValueError,'zero length|invalid geometry'):
            osm_geometries(elements,{1:(0,0),2:(0,0)})

    def test_open_building_fails_without_closing(self):
        elements=[{'type':'way','id':1,'nodes':[1,2,3],'tags':{'building':'yes'}}]
        with self.assertRaisesRegex(ValueError,'Unclosed area'):
            osm_geometries(elements,{1:(0,0),2:(1,0),3:(1,1)})

    def test_invalid_bowtie_fails_without_repair(self):
        elements=[{'type':'way','id':1,'nodes':[1,2,3,4,1],'tags':{'building':'yes'}}]
        with self.assertRaisesRegex(ValueError,'invalid geometry'):
            osm_geometries(elements,{1:(0,0),2:(1,1),3:(0,1),4:(1,0)})

if __name__=='__main__': unittest.main()
