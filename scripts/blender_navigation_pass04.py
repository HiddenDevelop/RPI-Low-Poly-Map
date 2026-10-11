"""Saved-file navigation presentation; no source or live-session changes."""
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import blender_pass03 as audit
RUN='rpi_navigation_20261011_pass04'
BASE=ROOT/'blender/working/rpi_lowpoly_20261011_pass03_r02_v01.blend'
OUT=ROOT/'blender/working'/f'{RUN}_v01.blend'
CP=ROOT/'blender/checkpoints'/f'{RUN}_before_changes.blend'
BASELINE=ROOT/'blender/checkpoints'/f'{RUN}_baseline.json.gz'
REPORT=ROOT/'blender/working'/f'{RUN}_validation.json'
DATA=ROOT/'gis/cleaned'/RUN
records=json.loads((DATA/'features.json').read_text())['records']
landscape=json.loads((DATA/'landscape_review.json').read_text())
original=json.loads((ROOT/'blender/working/rpi_lowpoly_20261010_01_payload.json').read_text())
origin=original['origin_projected_m']

def terrain(x,y):
    grid=original['terrain'];vs=grid['vertices'];nx=grid['nx'];ny=grid['ny']
    fx=(x-vs[0][0])/4;fy=(y-vs[0][1])/4
    assert 0<=fx<=nx-1 and 0<=fy<=ny-1
    ix=min(nx-2,int(fx));iy=min(ny-2,int(fy));u=fx-ix;v=fy-iy
    a=iy*nx+ix;z0,z1,z2,z3=[vs[i][2] for i in [a,a+1,a+nx,a+nx+1]]
    return z0+(z1-z0)*u+(z3-z1)*v if u>=v else z0+(z3-z2)*u+(z2-z0)*v

def mesh(name,verts,faces,col,mat,source_id):
    data=bpy.data.meshes.new(RUN+'_'+name);data.from_pydata(verts,[],faces);data.update()
    o=bpy.data.objects.new(data.name,data);col.objects.link(o);data.materials.append(mat)
    o['source_id']=source_id;o['geometry_role']='Navigation presentation, not measured clearance or certified route'
    return o

def tube(name,points,radius,col,mat,source_id):
    data=bpy.data.curves.new(RUN+'_'+name,'CURVE');data.dimensions='3D';data.bevel_depth=radius;data.bevel_resolution=1
    spline=data.splines.new('POLY');spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points):p.co=(*co,1)
    obj=bpy.data.objects.new(data.name,data);col.objects.link(obj);data.materials.append(mat)
    obj['source_id']=source_id;obj['geometry_role']='Illustrative rail/support or cartographic marker; not surveyed'
    return obj

def validate():
    before=json.loads(gzip.decompress(BASELINE.read_bytes()))
    root=bpy.data.collections[RUN];exceptions=json.loads(root['hidden_originals_json']);errors=[]
    for name,old in before['objects'].items():
        obj=bpy.data.objects.get(name)
        if obj is None:errors.append('Missing '+name);continue
        now=audit.state(obj)
        if name in exceptions:
            if not now['hide_render'] or not now['hide_viewport']:errors.append('Visibility '+name)
            for k in ['hide_render','hide_viewport']:now[k]=old[k]
        if now!=old:errors.append('Original changed '+name)
    for name,old in before['collections'].items():
        now=audit.normalized(audit.collection_state(bpy.data.collections[name]))
        if name=='DISPLAY_NONAUTHORITATIVE':now['children']=[n for n in now['children'] if n!=RUN]
        if now!=old:errors.append('Hierarchy changed '+name)
    if audit.normalized(audit.props(bpy.context.scene))!=before['scene_metadata']:errors.append('Scene metadata')
    initial=audit.original_validation();errors.extend(initial['errors'])
    max_error=0;stations=0;decks=0
    by_id={r['id']:r for r in records}
    expected_ids={r['id'] for r in records if r['feature']['geometry']['type']=='LineString'
        and r.get('display') and r['context']!='underground_or_transition'
        and (r['context']=='elevated' or r['display'].get('surface_display'))
        and len(r['display'].get('display_polyline',[]))>=2}
    actual_ids={o.get('source_id') for o in root.all_objects if o.get('centerline_payload')}
    if actual_ids!=expected_ids:errors.append('New display inventory mismatch')
    for o in root.all_objects:
        if not o.get('centerline_payload'):continue
        r=by_id[o['source_id']];points=r['display']['display_polyline']
        if len(o.data.vertices)!=3*len(points):errors.append('Stations '+o.name);continue
        expected_faces=[]
        for i in range(len(points)-1):
            a=i*3;expected_faces.extend([[a,a+3,a+4],[a,a+4,a+1],[a+1,a+4,a+5],[a+1,a+5,a+2]])
        if [list(p.vertices) for p in o.data.polygons]!=expected_faces:errors.append('New deck topology '+o.name)
        if o['display_width_m']!=r['display_width_m'] or o['width_status']!=r['width_status']:errors.append('Width metadata '+o.name)
        for i,p in enumerate(points):
            v=o.matrix_world@o.data.vertices[i*3+1].co
            max_error=max(max_error,abs(v.x-p[0]),abs(v.y-p[1]));stations+=1
        if o['source_tags_json']!=json.dumps(r['feature']['source'].get('tags',{}),sort_keys=True):errors.append('Tags '+o.name)
        if o.get('bridge')=='yes':decks+=1
    if max_error>.0001:errors.append('Centerline drift')
    if decks!=2:errors.append('Expected two bridge spans')
    for tree in landscape['trees']:
        if bpy.data.objects.get(RUN+'_CANOPY_'+tree['id'].split('/')[-1]) is None:errors.append('Missing canopy annotation')
    result={'passed':not errors,'errors':errors,'original_objects_compared':len(before['objects']),
        'original_collections_compared':len(before['collections']),'original_source_validation':initial,
        'visibility_exceptions':exceptions,'centerline_stations':stations,'max_centerline_xy_error_m':max_error,
        'bridge_decks':decks,'landscape_annotations':len(landscape['trees']),
        'baseline_sha256':hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
        'navigation_ready':False,'limitations':['Deck Z=73.8 m is illustrative, not converted from level/layer.',
        'Rail/support dimensions, widths without source tags, canopy sizes and plaza edges remain approximate.',
        'No accessibility inference, snapping or routing junction creation. Closure reopening unconfirmed.']}
    if REPORT.exists():assert json.loads(REPORT.read_text())==result
    else:audit.write_new(REPORT,result)
    print(json.dumps(result,indent=2));assert result['passed']

def apply():
    assert Path(bpy.data.filepath).resolve()==BASE.resolve()
    assert audit.original_validation()['passed']
    for p in [OUT,CP,BASELINE,REPORT]:assert not p.exists(),p
    before=audit.snapshot()
    with BASELINE.open('xb') as f:
        with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as z:z.write(json.dumps(before,sort_keys=True).encode())
    bpy.ops.wm.save_as_mainfile(filepath=str(CP),copy=True)
    root=bpy.data.collections.new(RUN);bpy.data.collections['DISPLAY_NONAUTHORITATIVE'].children.link(root)
    cols={}
    for key in ['SURFACES','ELEVATED','ENTRANCES','CANOPY_REVIEW']:
        c=bpy.data.collections.new(RUN+'_'+key);root.children.link(c);cols[key]=c
    palette={'concrete':(.76,.73,.62),'concrete:plates':(.59,.66,.68),'paving_stones':(.59,.38,.20),
             'unknown':(.53,.48,.43),'steps':(.74,.37,.16),'rail':(.16,.27,.29),
             'seam':(.27,.33,.32),'entrance':(.17,.46,.61),'leaf':(.28,.43,.16),'trunk':(.34,.22,.12)}
    mats={k:audit.material('pass04_'+k,v) for k,v in palette.items()}
    hidden=[];deck_z=73.8
    for r in records:
        f=r['feature'];key=r['id'];tags=f['source'].get('tags',{})
        if f['geometry']['type']!='LineString' or not r.get('display') or r['context']=='underground_or_transition':continue
        d=r['display'];elev=r['context']=='elevated'
        if not elev and not d.get('surface_display'):continue
        points=d.get('display_polyline',[])
        if len(points)<2:continue
        col=cols['ELEVATED' if elev else 'SURFACES'];width=r['display_width_m'];verts=[];faces=[]
        for i,p in enumerate(points):
            prev=points[max(0,i-1)];nxt=points[min(len(points)-1,i+1)]
            dx,dy=nxt[0]-prev[0],nxt[1]-prev[1];length=math.hypot(dx,dy);assert length>0
            nx,ny=-dy/length*width/2,dx/length*width/2
            for x,y in [(p[0]+nx,p[1]+ny),(p[0],p[1]),(p[0]-nx,p[1]-ny)]:
                verts.append([x,y,deck_z if elev else terrain(x,y)+.18])
        for i in range(len(points)-1):
            a=i*3;faces.extend([[a,a+3,a+4],[a,a+4,a+1],[a+1,a+4,a+5],[a+1,a+5,a+2]])
        kind='steps' if tags.get('highway')=='steps' else r['surface'] or 'unknown'
        obj=mesh('DECK_'+key.replace('/','_'),verts,faces,col,mats.get(kind,mats['unknown']),key)
        obj['centerline_payload']=True;obj['source_tags_json']=json.dumps(tags,sort_keys=True)
        obj['width_status']=r['width_status'];obj['display_width_m']=width;obj['bridge']=tags.get('bridge','unknown')
        obj['elevation_status']='Illustrative constant deck Z; not a layer-to-height conversion' if elev else 'Existing 4 m presentation DEM'
        for old in bpy.data.collections['rpi_lowpoly_20261010_pass02_PAVEMENT'].objects:
            if old.get('source_id')==key:
                old.hide_render=True;old.hide_viewport=True;hidden.append(old.name)
        # Slab joints and stair hatching indicate sourced type, never measured treads.
        if kind in ['concrete:plates','steps','paving_stones']:
            stride=1 if kind=='steps' else 2
            for i in range(1,len(points)-1,stride):
                a=verts[3*i][:];b=verts[3*i+2][:];a[2]+=.025;b[2]+=.025
                tube('JOINT_'+key.replace('/','_')+'_'+str(i),[a,b],.035,col,mats['seam'],key)
        if tags.get('bridge')=='yes':
            # Explicitly illustrative abutments at source endpoints; no invented support locations between them.
            for side in [0,2]:
                rail=[[verts[i*3+side][0],verts[i*3+side][1],deck_z+1.05] for i in range(len(points))]
                tube('RAIL_'+key.replace('/','_')+'_'+str(side),rail,.045,col,mats['rail'],key)
                for i in range(len(points)):
                    x,y,_=rail[i];tube('POST_'+key.replace('/','_')+f'_{side}_{i}',[[x,y,deck_z],[x,y,deck_z+1.05]],.045,col,mats['rail'],key)
            for i in [0,len(points)-1]:
                x,y=points[i][:2];tube('SUPPORT_'+key.replace('/','_')+'_'+str(i),[[x,y,terrain(x,y)],[x,y,deck_z]],.22,col,mats['rail'],key)
    for r in records:
        f=r['feature']
        if 'entrance' not in f['source'].get('tags',{}):continue
        x,y=f['geometry']['coordinates'];x-=origin[0];y-=origin[1]
        if r['context']=='underground_or_transition':continue
        z=deck_z if r['context']=='elevated' else terrain(x,y)+.25
        o=tube('ENTRY_'+r['id'].replace('/','_'),[[x,y,z],[x,y,z+1.6]],.18,cols['ENTRANCES'],mats['entrance'],r['id'])
        o['meaning']='Mapped entrance marker; accessibility unknown; not physical doorway dimensions'
    for tree in landscape['trees']:
        x,y=tree['geometry']['coordinates'];x-=origin[0];y-=origin[1];z=terrain(x,y)
        tube('TREE_TRUNK_'+tree['id'].split('/')[-1],[[x,y,z],[x,y,z+4]],.18,cols['CANOPY_REVIEW'],mats['trunk'],tree['id'])
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(x,y,z+4.7))
        o=bpy.context.object;o.name=RUN+'_CANOPY_'+tree['id'].split('/')[-1]
        for c in list(o.users_collection):c.objects.unlink(o)
        cols['CANOPY_REVIEW'].objects.link(o);r=tree['display_radius_m'];o.scale=(r,r,2.2);o.data.materials.append(mats['leaf'])
        o['source_id']=tree['id'];o['position_status']=tree['position_status'];o['routing_obstacle']='unknown'
    root['hidden_originals_json']=json.dumps(sorted(set(hidden)))
    root['closure_review_json']=(DATA/'closure_review.json').read_text()
    root['plaza_policy']='Approximate plaza envelope is available in plan-view review only; not applied as measured pavement.'
    camera=bpy.data.objects.new(RUN+'_Camera',bpy.data.cameras.new(RUN+'_Camera'));root.objects.link(camera)
    target=Vector((-37,28,73));camera.location=target+Vector((115,-210,200))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=285;camera.data.clip_end=10000
    caption=bpy.data.collections.new(RUN+'_CAPTIONS');root.children.link(caption)
    ink=bpy.data.materials.new(RUN+'_caption_ink');ink.use_nodes=True;ink.node_tree.nodes.clear()
    emission=ink.node_tree.nodes.new('ShaderNodeEmission');emission.inputs['Color'].default_value=(.04,.08,.08,1)
    output=ink.node_tree.nodes.new('ShaderNodeOutputMaterial');ink.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
    for label,body,y,size in [('title','JEC / DCC / GREENE',91,5),
        ('status','Bridge closure notice: reopening unconfirmed. Check campus signage.',-87,3.0),
        ('limits','Deck heights, untagged widths and canopy forms are illustrative.',-93,3.0)]:
        font=bpy.data.curves.new(RUN+'_caption_'+label,'FONT');font.body=body;font.size=size;font.materials.append(ink)
        obj=bpy.data.objects.new(font.name,font);caption.objects.link(obj);obj.parent=camera;obj.location=(-133,y,-100);obj.visible_shadow=False
    bpy.context.view_layer.update();validate();bpy.ops.wm.save_as_mainfile(filepath=str(OUT))

def render():
    assert Path(bpy.data.filepath).resolve()==OUT.resolve();validate()
    scene=bpy.context.scene
    for label,camera in [('overview',scene.camera),('district',bpy.data.objects[RUN+'_Camera'])]:
        p=ROOT/'renders'/f'{RUN}_{label}.png';assert not p.exists()
        scene.camera=camera;scene.render.filepath=str(p);scene.render.resolution_x=2100;scene.render.resolution_y=1500
        scene.render.resolution_percentage=100;scene.cycles.samples=40;scene.cycles.seed=0;scene.cycles.use_animated_seed=False
        bpy.data.collections['rpi_lowpoly_20261010_pass02_ANNOTATIONS'].hide_render=label!='overview'
        bpy.data.collections[RUN+'_CAPTIONS'].hide_render=label=='overview'
        bpy.ops.render.render(write_still=True)

def render_bridges():
    assert Path(bpy.data.filepath).resolve()==OUT.resolve();validate()
    scene=bpy.context.scene
    camera=bpy.data.objects.new(RUN+'_bridge_review_camera',bpy.data.cameras.new(RUN+'_bridge_review_camera'))
    scene.collection.objects.link(camera)
    target=Vector((-53,48,74));camera.location=target+Vector((15,160,140))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=210;camera.data.clip_end=10000
    p=ROOT/'renders'/f'{RUN}_north_walkways.png';assert not p.exists()
    scene.camera=camera;scene.render.filepath=str(p);scene.render.resolution_x=2100;scene.render.resolution_y=1300
    scene.render.resolution_percentage=100;scene.cycles.samples=40;scene.cycles.seed=0;scene.cycles.use_animated_seed=False
    bpy.data.collections['rpi_lowpoly_20261010_pass02_ANNOTATIONS'].hide_render=True
    bpy.data.collections[RUN+'_CAPTIONS'].hide_render=True
    bpy.ops.render.render(write_still=True)

if __name__=='__main__':
    for s in bpy.data.scenes:
        for v in s.view_layers:
            with bpy.context.temp_override(scene=s,view_layer=v):v.update()
    mode=sys.argv[sys.argv.index('--')+1]
    if mode=='inspect':audit.inspect()
    else:{'apply':apply,'validate':validate,'render':render,'render-bridges':render_bridges}[mode]()
