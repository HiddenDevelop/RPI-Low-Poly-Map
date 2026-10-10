import bpy, json, math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
ROOT='C:\\Users\\TheMa\\Documents\\Codex\\2026-10-09\\i-am-building-a-disability-accessible\\outputs\\rpi-access-map'
RUN='rpi_lowpoly_20261010_01'
SCENE='RPI_PILOT_rpi_lowpoly_20261010_01'
AUDIT_DOCS=json.loads(bpy.data.collections['RPI_AUDIT']['baseline_documents_json'])
PAYLOAD_DATA=json.loads(''.join(bpy.data.collections['RPI_INPUT_STAGING'][f'payload_{i:03d}'] for i in range(17)))
SOURCE_GRAPH_JSON=''.join(bpy.data.collections['RPI_INPUT_STAGING'][f'graph_{i:03d}'] for i in range(20))
DATUM_JSON=''.join(bpy.data.collections['RPI_INPUT_STAGING'][f'datum_{i:03d}'] for i in range(1))
def object_name(o):
    return o.name

def dump_new(path,value):
    AUDIT_DOCS[path]=value

def load_payload():
    return PAYLOAD_DATA

def plain(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    if hasattr(v,'to_dict'):return {k:plain(x) for k,x in v.to_dict().items()}
    if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
    if hasattr(v,'to_list'):return v.to_list()
    try:return [plain(x) for x in v]
    except TypeError:return str(v)

def props(x):return {k:plain(v) for k,v in x.items()}

def object_state(o):
    state={'name':o.name,'type':o.type,'world_transform':[list(r) for r in o.matrix_world],
      'local_transform':[list(r) for r in o.matrix_local],'parent':o.parent.name if o.parent else None,
      'collections':sorted(c.name for c in o.users_collection),'metadata':props(o),
      'library':o.library.filepath if o.library else None,'instance_type':o.instance_type,
      'instance_collection':o.instance_collection.name if o.instance_collection else None,
      'modifiers':[(m.name,m.type) for m in o.modifiers], 'constraints':[(c.name,c.type) for c in o.constraints],
      'hide_render':o.hide_render,'hide_viewport':o.hide_viewport,'hide_select':o.hide_select,
      'data_name':o.data.name if o.data else None,'data_metadata':props(o.data) if o.data else {}}
    if o.type=='MESH':
        state.update(vertices=[list(o.matrix_world@v.co) for v in o.data.vertices],
          edges=[list(e.vertices) for e in o.data.edges],faces=[list(p.vertices) for p in o.data.polygons],
          loops=[(l.vertex_index,l.edge_index) for l in o.data.loops],
          polygon_material_indices=[p.material_index for p in o.data.polygons])
    elif o.type=='CAMERA':
        state['camera']={'type':o.data.type,'lens':o.data.lens,'ortho_scale':o.data.ortho_scale,'clip_start':o.data.clip_start,'clip_end':o.data.clip_end}
    elif o.type=='LIGHT':state['light']={'type':o.data.type,'energy':o.data.energy,'color':list(o.data.color)}
    elif o.type=='CURVE':
        state['splines']=[{'type':s.type,'cyclic':s.use_cyclic_u,'points':[list(p.co) for p in s.points]} for s in o.data.splines]
    return state

def snapshot(names=None):
    objects=sorted(bpy.data.objects,key=object_name) if names is None else [bpy.data.objects[n] for n in sorted(names)]
    return {'objects':{o.name:object_state(o) for o in objects},
      'collections':{c.name:{'children':sorted(x.name for x in c.children),'objects':sorted(o.name for o in c.objects),'metadata':props(c),'library':c.library.filepath if c.library else None} for c in bpy.data.collections},
      'scenes':{s.name:{'children':sorted(c.name for c in s.collection.children),'objects':sorted(o.name for o in s.collection.objects),'metadata':props(s)} for s in bpy.data.scenes},
      'mode':bpy.context.mode,'active_scene':bpy.context.scene.name,'selection':sorted(o.name for o in bpy.context.selected_objects),
      'active_object':bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None}

def checkpoint(suffix):
    if suffix=='before_import':suffix='before_import_retry'
    path=ROOT+'/blender/checkpoints/'+RUN+'_'+suffix+'.blend'
    if bpy.data.collections.get('RPI_AUDIT'):
        bpy.data.collections['RPI_AUDIT']['baseline_documents_json']=json.dumps(AUDIT_DOCS,sort_keys=True)
    bpy.ops.wm.save_as_mainfile(filepath=path,copy=True)
    return path

def collection(name,parent):
    if bpy.data.collections.get(name):raise ValueError(f'Collection exists: {name}')
    c=bpy.data.collections.new(name);parent.children.link(c);return c

def mesh(name,vertices,edges,faces,col):
    if bpy.data.objects.get(name) or bpy.data.meshes.get(name):raise ValueError(f'Datablock exists: {name}')
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,edges,faces);data.update()
    o=bpy.data.objects.new(name,data);col.objects.link(o);return o

def import_stage():
    if bpy.context.mode!='OBJECT':raise RuntimeError('Stop: Blender must be in Object mode')
    if bpy.data.scenes.get(SCENE):raise ValueError('This run already exists')
    payload=load_payload()
    before=snapshot();dump_new((ROOT+'/blender/checkpoints/'+f'{RUN}_preimport.json'),before)
    cp=checkpoint('before_import')
    scene=bpy.data.scenes.new(SCENE);scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene['crs']=payload['crs'];scene['origin_projected_m']=payload['origin_projected_m']
    scene['geographic_transform']='Blender XY = EPSG:26918 XY minus origin. One Blender unit = one meter. No horizontal scale.'
    scene['source_z_status']=payload['source_z_status'];scene['pipeline_manifest_sha256']=payload['pilot_manifest_sha256']
    scene['datum_operation_accuracy_m']=4.0;scene['routing_status']='Visualization only; accessibility remains unknown unless explicitly tagged, and tags are unverified.'
    root=collection('RPI_PILOT',scene.collection);root['source_manifest_sha256']=payload['pilot_manifest_sha256']
    audit=collection('RPI_AUDIT',root)
    audit['source_graph_json']=SOURCE_GRAPH_JSON
    audit['source_graph_sha256']=payload['source_graph_sha256']
    audit['datum_operations_json']=DATUM_JSON
    source=collection('GIS_SOURCE_LOCKED',root)
    cols={name:collection(name,source) for name in ['TERRAIN_LOCKED','BUILDINGS','PATHS_LOCKED','ROADS','ACCESSIBILITY_LOCKED','ENTRANCES_LOCKED','LANDCOVER_LOCKED']}
    origin=payload['origin_projected_m'];objs=[]
    mapping={'buildings':'BUILDINGS','paths':'PATHS_LOCKED','stairs':'PATHS_LOCKED','roads':'ROADS','entrances':'ENTRANCES_LOCKED','accessibility':'ACCESSIBILITY_LOCKED','landcover':'LANDCOVER_LOCKED'}
    for d in payload['features']:
        f=d['feature'];g=f['geometry'];coords=g['coordinates'];key=f['id'];verts=[];edges=[]
        if g['type']=='Point':verts=[(coords[0]-origin[0],coords[1]-origin[1],0)]
        elif g['type']=='LineString':
            verts=[(p[0]-origin[0],p[1]-origin[1],0) for p in coords];edges=[(i,i+1) for i in range(len(verts)-1)]
        elif g['type']=='Polygon':
            for ring in coords:
                start=len(verts);verts.extend((p[0]-origin[0],p[1]-origin[1],0) for p in ring[:-1]);n=len(ring)-1
                edges.extend((start+i,start+(i+1)%n) for i in range(n))
        else:raise ValueError(g['type'])
        memberships=sorted({mapping[x] for x in d['layers']})
        o=mesh('GIS_'+key.replace('/','_'),verts,edges,[],cols[memberships[0]])
        for c in memberships[1:]:cols[c].objects.link(o)
        o['source_id']=key;o['source_record_json']=json.dumps(f['source'],sort_keys=True)
        o['geometry_json']=json.dumps(g,sort_keys=True);o['layers_json']=json.dumps(d['layers']);o['scope']=f['scope']
        o['z_status']='Unknown in vector source; zero placeholder only';o['authoritative_xy']=True
        o['origin_projected_m']=origin;o['crs']='EPSG:26918'
        o.hide_render=True;o.hide_viewport=True;o.hide_select=True;objs.append(o.name)
    terrain=payload['terrain'];nx,ny=terrain['nx'],terrain['ny'];faces=[]
    for y in range(ny-1):
        for x in range(nx-1):
            a=y*nx+x;b=a+1;c=a+nx;d=c+1
            faces.extend([(a,b,d),(a,d,c)])
    ground=mesh('GIS_TERRAIN_4M_PRESENTATION',terrain['vertices'],[],faces,cols['TERRAIN_LOCKED'])
    ground['source']=terrain['source'];ground['source_sha256']=terrain['source_sha256'];ground['vertical_datum']='NAVD88 meters'
    ground['sampling']='4 m presentation approximation of native 1 m DEM, not routing terrain';ground['origin_projected_m']=origin
    ground.hide_select=True;objs.append(ground.name)
    # Capture all new source data and unrelated original objects, including collection links.
    bpy.context.view_layer.update()
    baseline=snapshot();dump_new((ROOT+'/blender/checkpoints/'+f'{RUN}_source_baseline.json'),baseline)
    report=validate_import(payload)
    dump_new((ROOT+'/blender/working/'+f'{RUN}_import_validation.json'),report)
    if not report['passed']:raise RuntimeError(report)
    cp2=checkpoint('before_styling')
    print(json.dumps({'scene':SCENE,'source_objects':len(objs),'checkpoint_before_import':cp,'checkpoint_before_styling':cp2,'import_validation':report}))

def validate_import(payload):
    origin=payload['origin_projected_m'];errors=[];max_error=0;count=0
    for d in payload['features']:
        f=d['feature'];g=f['geometry'];o=bpy.data.objects.get('GIS_'+f['id'].replace('/','_'))
        if not o:errors.append(f"Missing {f['id']}");continue
        require=json.loads(o['source_record_json'])==f['source'] and json.loads(o['geometry_json'])==g
        if not require:errors.append(f"Metadata {f['id']}")
        coords=[g['coordinates']] if g['type']=='Point' else g['coordinates'] if g['type']=='LineString' else [p for r in g['coordinates'] for p in r[:-1]]
        if len(coords)!=len(o.data.vertices):errors.append(f"Vertex count {f['id']}");continue
        for v,p in zip(o.data.vertices,coords):
            q=o.matrix_world@v.co;error=max(abs(q.x+origin[0]-p[0]),abs(q.y+origin[1]-p[1]));max_error=max(max_error,error)
            if error>0.0001:errors.append(f"XY mismatch {f['id']}")
        edges=[]
        if g['type']=='LineString':edges=[(i,i+1) for i in range(len(coords)-1)]
        elif g['type']=='Polygon':
            start=0
            for ring in g['coordinates']:
                n=len(ring)-1;edges.extend((start+i,start+(i+1)%n) for i in range(n));start+=n
        expected=sorted(tuple(sorted(e)) for e in edges);actual=sorted(tuple(sorted(e.vertices)) for e in o.data.edges)
        if expected!=actual:errors.append(f"Edges {f['id']}")
        if len(o.data.polygons)!=0:errors.append('Unexpected source faces')
        count+=1
    if bpy.data.collections['RPI_AUDIT']['source_graph_json']!=SOURCE_GRAPH_JSON:errors.append('Embedded graph changed')
    return {'passed':not errors,'errors':errors,'features_verified':count,'maximum_xy_float32_error_m':max_error,
      'tolerance_m':0.0001,'source_graph_preserved':True,'note':'Blender float32 requires documented tolerance; GIS JSON remains exact. No geographic data shifted for appearance.'}

def mat(name,color,roughness=0.85):
    m=bpy.data.materials.new(RUN+'_'+name);m.diffuse_color=(*color,1);m.use_nodes=True
    node=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=roughness
    return m

def style_stage():
    if bpy.context.mode!='OBJECT':raise RuntimeError('Object mode required')
    payload=load_payload();scene=bpy.data.scenes[SCENE];root=bpy.data.collections['RPI_PILOT']
    display=collection('DISPLAY_NONAUTHORITATIVE',root)
    buildings=collection('DISPLAY_BUILDINGS',display);routes=collection('DISPLAY_SURFACE_LINES',display);decor=collection('DISPLAY_PRESENTATION',display)
    colors=[(0.61,0.24,0.16),(0.72,0.35,0.24),(0.77,0.48,0.30),(0.78,0.65,0.46),(0.58,0.30,0.22)]
    walls=[mat('warm_facade_'+str(i),c) for i,c in enumerate(colors)]
    roofs=[mat('roof_slate',(0.23,0.31,0.32)),mat('roof_sand',(0.73,0.67,0.52)),mat('roof_clay',(0.46,0.23,0.16))]
    grass=mat('meadow',(0.48,0.59,0.34));soil=mat('earth_edge',(0.37,0.29,0.20));pathmat=mat('walkways',(0.92,0.84,0.65))
    roadmat=mat('roads',(0.38,0.43,0.43));stairmat=mat('stairs',(0.85,0.46,0.23));plinthmat=mat('warm_backdrop',(0.87,0.83,0.72))
    ground=bpy.data.objects['GIS_TERRAIN_4M_PRESENTATION'];ground.data.materials.append(grass)
    # Material-only styling of protected terrain: topology, positions and metadata remain untouched.
    origin=payload['origin_projected_m'];display_buildings=[];omitted=[];line_count=0
    for index,d in enumerate(payload['features']):
        f=d['feature'];g=f['geometry'];key=f['id']
        if 'buildings' in d['layers']:
            if g['type']!='Polygon' or len(g['coordinates'])!=1:raise ValueError('Complex footprint needs explicit styling implementation')
            coords=g['coordinates'][0][:-1];n=len(coords);base=d['ground_base'];roof=max(d['ground_center']+d['display_height_m'],max(d['ground_samples'])+4)
            xy=[(p[0]-origin[0],p[1]-origin[1]) for p in coords]
            verts=[(x,y,base) for x,y in xy]+[(x,y,roof) for x,y in xy]
            faces=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
            ring=[Vector((x,y,roof)) for x,y in xy];lookup={tuple(v):i+n for i,v in enumerate(ring)}
            topfaces=[tuple(v+n if isinstance(v,int) else lookup[tuple(v)] for v in tri) for tri in tessellate_polygon([ring])];faces+=topfaces
            o=mesh('VIS_'+key.replace('/','_'),verts,[],faces,buildings)
            color_index=sum((i+1)*ord(c) for i,c in enumerate(key))%len(walls)
            o.data.materials.append(walls[color_index]);o.data.materials.append(roofs[color_index%len(roofs)])
            for p in o.data.polygons:p.material_index=1 if p.index>=n else 0
            o['source_id']=key;o['height_status']=d['height_status'];o['geometry_role']='Presentation extrusion; XY boundary copied exactly, no bevel or footprint simplification'
            o['source_name']=f['source'].get('tags',{}).get('name','Unnamed building');display_buildings.append(o)
        elif g['type']=='LineString' and any(k in d['layers'] for k in ['paths','roads','stairs']):
            if not d['surface_display']:omitted.append(key);continue
            cat='roads' if 'roads' in d['layers'] else 'stairs' if 'stairs' in d['layers'] else 'paths'
            width=4.0 if cat=='roads' else 1.6 if cat=='paths' else 1.5
            curve=bpy.data.curves.new('VIS_'+key.replace('/','_'),'CURVE');curve.dimensions='3D';curve.resolution_u=1;curve.bevel_resolution=0;curve.bevel_depth=width/2
            spline=curve.splines.new('POLY');spline.points.add(len(d['display_polyline'])-1)
            for p,co in zip(spline.points,d['display_polyline']):p.co=(*co,1)
            o=bpy.data.objects.new(curve.name,curve);routes.objects.link(o);curve.materials.append(roadmat if cat=='roads' else stairmat if cat=='stairs' else pathmat)
            o['source_id']=key;o['display_width_m']=width;o['width_status']='Illustrative width, not measured clearance';o['elevation_status']=d['display_note'];line_count+=1
    # A low-poly soil edge follows the terrain perimeter exactly at the top.
    tv=payload['terrain']['vertices'];nx=payload['terrain']['nx'];ny=payload['terrain']['ny']
    perimeter=list(range(nx))+[y*nx+nx-1 for y in range(1,ny)]+[(ny-1)*nx+x for x in range(nx-2,-1,-1)]+[y*nx for y in range(ny-2,0,-1)]
    floor=min(v[2] for v in tv)-8;edgeverts=[tv[i] for i in perimeter]+[[tv[i][0],tv[i][1],floor] for i in perimeter];n=len(perimeter)
    edge=mesh('VIS_Terrain_Edge',edgeverts,[],[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],decor);edge.data.materials.append(soil)
    bounds=[min(v[0] for v in tv),min(v[1] for v in tv),max(v[0] for v in tv),max(v[1] for v in tv)]
    cx=(bounds[0]+bounds[2])/2;cy=(bounds[1]+bounds[3])/2
    backing=mesh('VIS_Backdrop',[(cx-2500,cy-2500,floor-0.5),(cx+2500,cy-2500,floor-0.5),(cx+2500,cy+2500,floor-0.5),(cx-2500,cy+2500,floor-0.5)],[],[(0,1,2,3)],decor);backing.data.materials.append(plinthmat)
    world=bpy.data.worlds.new(RUN+'_World');world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(0.77,0.84,0.88,1);world.node_tree.nodes.get('Background').inputs[1].default_value=0.7;scene.world=world
    lightdata=bpy.data.lights.new(RUN+'_Sun','SUN');lightdata.energy=2.6;lightdata.angle=math.radians(12)
    light=bpy.data.objects.new(lightdata.name,lightdata);decor.objects.link(light);light.rotation_euler=(math.radians(28),math.radians(-20),math.radians(-25))
    camera_data=bpy.data.cameras.new(RUN+'_Camera');camera=bpy.data.objects.new(camera_data.name,camera_data);decor.objects.link(camera)
    target=Vector((cx,cy,50));camera.location=target+Vector((190,-680,850));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.clip_end=10000
    camera_data.ortho_scale=1250;scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=1800;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str((ROOT+'/renders/'+f'{RUN}_overview.png'))
    scene.render.film_transparent=False
    # Place a compact caption in the camera plane; it is presentation text, not a GIS label.
    ink=mat('caption_ink',(0.12,0.18,0.18))
    bsdf=next(n for n in ink.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bsdf.inputs['Emission Color'].default_value=(0.12,0.18,0.18,1);bsdf.inputs['Emission Strength'].default_value=1
    def caption(name,text,x,y,size):
        data=bpy.data.curves.new(name,'FONT');data.body=text;data.size=size;data.extrude=0
        o=bpy.data.objects.new(name,data);decor.objects.link(o);o.parent=camera;o.location=(x,y,-100);o.data.materials.append(ink)
    caption('VIS_Title','RPI / CORE CAMPUS',-555,402,23)
    caption('VIS_Subtitle','A warm, low-poly study of the validated GIS pilot',-555,376,10)
    caption('VIS_Footer','OSM + USGS 3DEP  /  Illustrative heights and path widths  /  Accessibility unverified',-555,-419,9)
    scene['styling_notes']='Warm facades, simple flat roofs, low-poly DEM presentation. No decorative trees added because tree locations are not sourced. Indoor/nonzero level paths retained in source, omitted from surface overview.'
    scene['omitted_surface_display_ids']=json.dumps(omitted)
    dump_new((ROOT+'/blender/working/'+f'{RUN}_style_log.json'),{'building_count':len(display_buildings),'surface_line_count':line_count,'omitted_surface_lines':omitted,'terrain_grid_spacing_m':4,'footprint_simplification':False,'seed':'Weighted source ID character sum palette selection; no randomness'})
    print(json.dumps({'display_buildings':len(display_buildings),'surface_lines':line_count,'omitted_indoor_or_multilevel_lines':len(omitted),'render_path':scene.render.filepath}))

def validate_stage():
    baseline=AUDIT_DOCS[ROOT+'/blender/checkpoints/'+RUN+'_source_baseline.json']
    payload=load_payload();now=snapshot(baseline['objects']);errors=[]
    for name,before in baseline['objects'].items():
        after=now['objects'][name]
        if before!=after:errors.append({'object':name,'changed_fields':[k for k in before if before[k]!=after.get(k)]})
    for name,before in baseline['collections'].items():
        if name in ('RPI_PILOT','RPI_AUDIT'):continue # presentation sibling is intentionally added here
        after=now['collections'].get(name)
        if before!=after:errors.append({'collection':name,'change':'membership/metadata/hierarchy'})
    pre=AUDIT_DOCS[ROOT+'/blender/checkpoints/'+RUN+'_preimport.json']
    for name,before in pre['objects'].items():
        if object_state(bpy.data.objects[name])!=before:errors.append({'unrelated_object':name})
    for name,before in pre['scenes'].items():
        if now['scenes'][name]!=before:errors.append({'unrelated_scene':name})
    # Inspect display footprint boundaries too, including every extrusion base/top pair.
    max_visual_error=0
    for d in payload['features']:
        if 'buildings' not in d['layers']:continue
        f=d['feature'];o=bpy.data.objects['VIS_'+f['id'].replace('/','_')];coords=f['geometry']['coordinates'][0][:-1];origin=payload['origin_projected_m']
        if len(o.data.vertices)!=2*len(coords):errors.append({'display_building_vertex_count':f['id']});continue
        for i,v in enumerate(o.data.vertices):
            p=coords[i%len(coords)];q=o.matrix_world@v.co;err=max(abs(q.x+origin[0]-p[0]),abs(q.y+origin[1]-p[1]));max_visual_error=max(max_visual_error,err)
            if err>0.0001:errors.append({'display_footprint_shift':f['id']})
    imported=validate_import(payload)
    if not imported['passed']:errors.extend(imported['errors'])
    if bpy.context.mode!=pre['mode'] or sorted(o.name for o in bpy.context.selected_objects)!=pre['selection']:errors.append('Mode/selection changed')
    report={'passed':not errors,'errors':errors,'baseline_objects_compared':len(baseline['objects']),
      'protected_geometry_checks':['exact world transforms','exact world-space vertex coordinates','edge/polygon/loop topology','custom metadata','nested collection children and linked memberships','unchanged modifier/constraint lists','embedded source graph hash'],
      'max_display_footprint_error_m':max_visual_error,'import_validation':imported,'unrelated_scene_objects_unchanged':not errors,
      'presentation_only_changes':'New display meshes/materials, camera, light, world, captions; terrain material assignment only.',
      'limitations':'Rendering estimates are not routing data. DEM presentation grid is approximate. No accessibility values inferred.'}
    dump_new((ROOT+'/blender/working/'+f'{RUN}_style_validation.json'),report)
    if errors:raise RuntimeError(report)
    path=(ROOT+'/blender/working/'+f'{RUN}_styled.blend')
    bpy.data.collections['RPI_AUDIT']['baseline_documents_json']=json.dumps(AUDIT_DOCS,sort_keys=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path),copy=True)
    print(json.dumps({'validation':report,'working_blend':str(path),'active_scene_preserved':bpy.context.scene.name}))
style_stage()
validate_stage()
