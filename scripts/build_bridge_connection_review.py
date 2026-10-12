"""Build an evidence-only bridge review without changing any geographic source.

Usage: python scripts/build_bridge_connection_review.py --out NEW_DIRECTORY
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'gis/cleaned/rpi_navigation_20261011_pass04'
PLANS = ROOT / 'gis/acquisitions/quacs_floorplans_20261011_01'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write('\n')


def build(out):
    out.mkdir(parents=True, exist_ok=False)
    inputs = [BASE / n for n in ('features.json', 'source_topology.json', 'closure_review.json')]
    inputs += [ROOT / 'gis/cleaned/pilot/osm/buildings.json', PLANS / 'manifest.json']
    inputs += sorted(PLANS.glob('*.pdf'))
    hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in inputs}
    for line in (PLANS / 'SHA256SUMS.txt').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert digest(PLANS / name) == expected, name
    doc = read(BASE / 'features.json')
    top = read(BASE / 'source_topology.json')
    features = {r['id']: r['feature'] for r in doc['records']}
    reviews = []
    for number, (node, incident) in enumerate(sorted(top['mixed_level_nodes'].items(), key=lambda x:int(x[0])), 1):
        coordinates = []
        for entry in incident:
            f = features[entry['source_id']]
            assert f['source']['nodes'][entry['index']] == int(node)
            coordinates.append(f['geometry']['coordinates'][entry['index']])
        assert all(p == coordinates[0] for p in coordinates)
        reviews.append(dict(id=f'T{number}', kind='shared_node_level_review', source_node_id=f'osm/node/{node}',
                            geometry=dict(type='Point', coordinates=coordinates[0]), incidence=incident,
                            status='unresolved', accessibility=None,
                            decision='Preserve shared source node; do not infer a usable floor transition from layer tags.'))
    for number, crossing in enumerate(top['geometric_crossing_review'], 1):
        a, b = [features[k] for k in crossing['source_ids']]
        assert not set(a['source']['nodes']) & set(b['source']['nodes'])
        reviews.append(dict(id=f'X{number}', kind='crossing_without_shared_node',
                            geometry=crossing['geometry'], source_ids=crossing['source_ids'],
                            status='source_topology_preserved', accessibility=None,
                            decision='No connection added. Crossing geometry alone does not establish connectivity.'))
    candidates = [
        dict(id='P1', source_ids=['osm/way/104737241'], plans=['jonssonengctr3000.pdf'],
             observation='Historical JEC 3000 balcony zones 3000B/C/D and open-to-below areas.',
             proposal='Review display massing for balcony and undercroft openings after geographic alignment.'),
        dict(id='P2', source_ids=['osm/way/284529300', 'osm/node/2872820222'], plans=['jonssonengctr3000.pdf', 'darrin-3.pdf'],
             observation='Historical JEC 3000 and DCC 300 sheets depict vestibules and exterior approaches.',
             proposal='Verify bridge endpoints, physical floor correspondence and current closure before model or routing changes.'),
        dict(id='P3', source_ids=['osm/way/104737300', 'osm/node/2870374473'], plans=['jonssonengctr3000.pdf', 'greene-1.pdf'],
             observation='Greene 100 sheet depicts vestibule 100F, stair 100E and elevator 1-E near one end.',
             proposal='Confirm orientation and actual approach; an elevator symbol does not establish a step-free route.')]
    for c in candidates:
        c.update(status='historical_candidate_only', geographic_transform=None, floor_correspondence=None,
                 control_points=[], residual_m=None, geometry_edit_approved=False)
    evidence = dict(crs='EPSG:26918', units='metres', origin_offset=None,
                    datum_operation='None; existing projected coordinates copied exactly. PDF plans remain unregistered.',
                    navigation_ready=False, reviews=reviews, plan_candidates=candidates,
                    current_notice=dict(source_url=read(BASE/'closure_review.json')['source_url'], reviewed='2026-10-11',
                                        status='Reopening unconfirmed; approximate duration is not an end date.',
                                        linked_drawings_status='Box browser access denied by permission policy; drawings not inspected.'),
                    geometry_gate=dict(allowed=False, blockers=['No verified plan-to-GIS registration',
                         'Current entrance and elevator connectivity unconfirmed', 'Current detour drawings unavailable']))
    write(out / 'connection_review.json', evidence)
    # Complete source records, with ordered nodes and all unknowns, retained separately from review opinions.
    write(out / 'source_snapshot.json', dict(features=doc, topology=top))
    fig, ax = plt.subplots(figsize=(13, 8), layout='constrained')
    fig.get_layout_engine().set(rect=(0, .05, 1, .95))
    fig.set_facecolor('#f5f2e9'); ax.set_facecolor('#e5ead8')
    origin = [607920, 4731500]
    def local(p): return (p[0]-origin[0], p[1]-origin[1])
    buildings = read(ROOT/'gis/cleaned/pilot/osm/buildings.json')['features']
    for f in buildings:
        if f['geometry']['type'] != 'Polygon': continue
        ring = [local(p) for p in f['geometry']['coordinates'][0]]
        ax.add_patch(Polygon(ring, facecolor='#c9bba2', edgecolor='#a49883', linewidth=.7))
        if f['id'] in ('osm/way/104737202','osm/way/104737275','osm/way/104737313'):
            labels={'osm/way/104737202':'GREENE','osm/way/104737275':'JEC','osm/way/104737313':'DCC'}
            ax.text(sum(p[0] for p in ring)/len(ring),sum(p[1] for p in ring)/len(ring),labels[f['id']],ha='center',fontweight='bold',color='#394b48')
    for r in doc['records']:
        f=r['feature']; g=f['geometry']; tags=f['source'].get('tags',{})
        if g['type']=='Point': continue
        c=[local(p) for p in g['coordinates']]
        color='#ad4b3c' if tags.get('highway')=='steps' else '#16838b' if r['context']=='elevated' else '#8b847b'
        ax.plot(*zip(*c),color=color,lw=3 if tags.get('bridge')=='yes' else 1.1,
                linestyle='--' if r['context']=='underground_or_transition' else '-')
    for r in reviews:
        x,y=local(r['geometry']['coordinates']); crossing=r['id'].startswith('X')
        ax.scatter([x],[y],marker='x' if crossing else 'o',s=60,color='#af3d76' if crossing else '#bd771b',zorder=5)
        offset={'T3':(10,-17),'T4':(10,8),'T5':(-25,12),'T6':(10,12),'T7':(-28,-14),'X1':(8,-20),'X2':(-26,-22),'X3':(-27,10)}.get(r['id'],(7,8))
        ax.annotate(r['id'],(x,y),xytext=offset,textcoords='offset points',fontsize=10,fontweight='bold',
                    bbox=dict(boxstyle='round,pad=.2',fc='#fffdf7',ec='#b7b0a1'),arrowprops=dict(arrowstyle='-',color='#666'),zorder=6)
    ax.set(xlim=(0,255),ylim=(16,213),aspect='equal',xlabel='Metres east of 607920 (EPSG:26918)',ylabel='Metres north of 4731500 (EPSG:26918)')
    ax.set_title('JEC - DCC - Greene | connection review\n8 unresolved shared-node transitions; 3 crossings kept unconnected',loc='left',pad=15,fontweight='bold')
    ax.legend(handles=[Line2D([],[],color='#16838b',label='Elevated source ways'),Line2D([],[],color='#ad4b3c',label='Stairs'),
                       Line2D([],[],marker='o',color='#bd771b',linestyle='',label='T: transition review'),
                       Line2D([],[],marker='x',color='#af3d76',linestyle='',label='X: no shared node')],loc='lower left',fontsize=9)
    fig.text(.5,.015,'Evidence review only - no directions. Line widths are symbols. All source geometry is unchanged. North is up.',ha='center',fontsize=9)
    fig.savefig(out/'connection_overview.png',dpi=160,metadata={'Software':'RPI deterministic bridge review'}); plt.close(fig)
    snapshot=read(out/'source_snapshot.json')
    assert snapshot['features']==doc and snapshot['topology']==top
    assert all(digest(ROOT/p)==h for p,h in hashes.items())
    write(out/'validation.json',dict(passed=True,input_files_unchanged=len(hashes),input_sha256=hashes,
        full_source_records_exact=len(features),ordered_segments_exact=len(top['segments']),
        mixed_level_reviews=len(top['mixed_level_nodes']),unconnected_crossings=len(top['geometric_crossing_review']),
        original_node_order_and_unknowns_preserved=True,geographic_edits=0,blender_edits=0,navigation_ready=False))
    lines = ['# Bridge connection review', '',
        'A source-topology review, not an accessible route map. Reviewed 2026-10-11.', '',
        '![Connection overview](connection_overview.png)', '',
        '## Findings', '',
        'The historical sheets provide architectural clues but no verified geographic registration or current accessibility status. '
        'No plan floor number has been converted to an OSM level or physical height. No datum operations were performed. '
        'Original EPSG:26918 coordinates, boundary-crossing features, all ordered source nodes and unknown values remain unchanged.', '',
        '| Review | Source node / ways | Decision |', '| --- | --- | --- |']
    for r in reviews:
        ids = r.get('source_ids') or [r['source_node_id']] + [e['source_id'] for e in r['incidence']]
        lines.append('| '+r['id']+' | '+', '.join(ids)+' | '+r['decision']+' |')
    lines += ['', '## Historical plan candidates', '']
    for c in candidates:
        links=', '.join('['+n+'](../../acquisitions/quacs_floorplans_20261011_01/'+n+')' for n in c['plans'])
        lines += ['* **'+c['id']+'**: '+c['observation']+' '+c['proposal']+' Sources: '+links+'.']
    lines += ['', '## Current operational evidence', '',
        '[RPI closure notice](https://administration.rpi.edu/announcements/dcc-jec-upper-deck-walkway-closure) '
        'still gives an approximate closure duration, not a confirmed reopening. Its linked official drawings could not be inspected: '
        'browser access to RPI Box was denied by permission policy. No alternate access was attempted after that denial.', '',
        '## Next geometry gate', '',
        'Before a new Blender checkpoint: establish plan orientation and geographic control matches with residuals; '
        'confirm current bridge endpoints, entrances and elevators; distinguish undercroft openings from enclosed areas. '
        'Historical symbols alone cannot meet these requirements. No Blender objects were edited in this review.', '',
        '## Reproduction and validation', '',
        '`python scripts/build_bridge_connection_review.py --out NEW_DIRECTORY` from the project root '
        '(existing GIS Python environment with matplotlib). Output directories must be new. '
        'The builder verifies the floor-plan seal, shared-node coordinate identity, unconnected crossings, '
        'complete snapshot equality and input byte hashes. Original independent navigation validation also passes: '
        '95 features, 307 ordered segments, 304 incident nodes. This does not constitute route certification.', '',
        'Sources: OpenStreetMap contributors (original pilot provenance applies); pinned QuACS archive '
        '`08c82580638b3e9a3816802f3e1ba98a30383f13` (retained MIT license; original drawing rights uncertain); '
        'RPI Administration notice. NYS data remains separate. Source acquisition dates and hashes are retained in the input manifests.']
    with (out/'README.md').open('x',encoding='utf-8',newline='\n') as f:
        f.write('\n'.join(lines)+'\n')
    write(out/'manifest.json',{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    print(out)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--out',type=Path,required=True)
    build(parser.parse_args().out)
