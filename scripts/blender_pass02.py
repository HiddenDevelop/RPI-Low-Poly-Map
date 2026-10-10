"""Deterministic live-Blender presentation pass; execute through the prepared runner.

Host runner supplies snapshot helpers and LANDMARKS, then calls begin_pass02().
Protected source objects are never modified. Original display curves are retained.
All roof rises, window bays, path widths and symbols are presentation estimates.
"""
RUN2='rpi_lowpoly_20261010_pass02'
SAVED_PATH2=bpy.data.filepath.replace('\\','/')
if '/blender/' not in SAVED_PATH2:raise RuntimeError('Open the project pilot from its blender directory first')
ROOT2=SAVED_PATH2.rsplit('/blender/',1)[0]
PAYLOAD2=json.loads(''.join(bpy.data.collections['RPI_INPUT_STAGING'][f'payload_{i:03d}'] for i in range(17)))

def original_validation():
    audit=bpy.data.collections['RPI_AUDIT']
    docs=json.loads(audit['baseline_documents_json'])
    baseline=None
    for path,value in docs.items():
        if path.endswith('_source_baseline.json'):baseline=value
    if baseline is None:raise RuntimeError('Missing full source baseline')
    errors=[]
    for name,before in baseline['objects'].items():
        if name not in bpy.data.objects:
            errors.append('Missing object '+name);continue
        after=json.loads(json.dumps(object_state(bpy.data.objects[name])))
        if after!=before:errors.append('Protected object changed '+name)
    for name,before in baseline['collections'].items():
        if name in ('RPI_PILOT','RPI_AUDIT'):continue
        col=bpy.data.collections.get(name)
        if not col:errors.append('Missing collection '+name);continue
        now={'children':sorted(x.name for x in col.children),'objects':sorted(o.name for o in col.objects),
             'metadata':props(col),'library':col.library.filepath if col.library else None}
        if json.loads(json.dumps(now))!=before:errors.append('Source hierarchy changed '+name)
    stage=bpy.data.collections['RPI_INPUT_STAGING']
    graph=''.join(stage[f'graph_{i:03d}'] for i in range(20))
    if audit['source_graph_json']!=graph:errors.append('Embedded graph differs from source staging')
    return {'passed':not errors,'errors':errors,'baseline_objects_compared':len(baseline['objects']),
      'checks':['exact world transforms and world-space vertices','edges, faces and loops',
      'source metadata and ordered topology','nested collection hierarchy and linked memberships',
      'source graph including ordered relation members and multilevel tags']}

def material2(name,color,emission=False):
    m=bpy.data.materials.new(RUN2+'_'+name);m.diffuse_color=(*color,1);m.use_nodes=True
    node=m.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=0.85
    if emission:
        m.node_tree.nodes.clear()
        shader=m.node_tree.nodes.new('ShaderNodeEmission');shader.inputs['Color'].default_value=(*color,1)
        output=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(shader.outputs[0],output.inputs['Surface'])
    return m

def mesh2(name,verts,faces,col,mat):
    data=bpy.data.meshes.new(RUN2+'_'+name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(data.name,data);col.objects.link(obj)
    if mat: data.materials.append(mat)
    obj['geometry_role']='Presentation only; not routing geometry or measured accessibility data'
    return obj

def collection2(name,parent):
    col=bpy.data.collections.new(RUN2+'_'+name);parent.children.link(col);return col

def terrain2(x,y):
    grid=PAYLOAD2['terrain'];nx=grid['nx'];ny=grid['ny'];vs=grid['vertices']
    fx=(x-vs[0][0])/4;fy=(y-vs[0][1])/4
    if fx<0 or fy<0 or fx>nx-1 or fy>ny-1:raise RuntimeError('Display outside DEM grid')
    ix=min(nx-2,int(fx));iy=min(ny-2,int(fy));u=fx-ix;v=fy-iy
    a=iy*nx+ix;z0=vs[a][2];z1=vs[a+1][2];z2=vs[a+nx][2];z3=vs[a+nx+1][2]
    if u>=v:return z0+(z1-z0)*u+(z3-z1)*v
    return z0+(z3-z2)*u+(z2-z0)*v

def line2(name,coords,width,col,mat):
    data=bpy.data.curves.new(RUN2+'_'+name,'CURVE');data.dimensions='3D'
    data.resolution_u=1;data.bevel_depth=width;data.bevel_resolution=0
    spline=data.splines.new('POLY');spline.points.add(len(coords)-1)
    for p,co in zip(spline.points,coords):p.co=(*co,1)
    obj=bpy.data.objects.new(data.name,data);col.objects.link(obj);data.materials.append(mat)
    obj['geometry_role']='Presentation annotation, not a route'
    return obj

def text2(name,body,x,y,size,col,mat,camera):
    data=bpy.data.curves.new(RUN2+'_'+name,'FONT');data.body=body;data.size=size
    obj=bpy.data.objects.new(data.name,data);col.objects.link(obj);obj.parent=camera
    obj.location=(x,y,-90);data.materials.append(mat);obj.visible_shadow=False
    return obj

def begin_pass02():
    if bpy.context.mode!='OBJECT':raise RuntimeError('Object mode required')
    if bpy.data.collections.get(RUN2+'_AUDIT'):raise RuntimeError('Run exists; use a new unique run ID')
    initial=original_validation()
    if not initial['passed']:raise RuntimeError(json.dumps(initial))
    checkpoint=ROOT2+'/blender/checkpoints/'+RUN2+'_before_changes.blend'
    bpy.ops.wm.save_as_mainfile(filepath=checkpoint,copy=True)
    scene=bpy.context.scene
    if scene.name!='RPI_PILOT_rpi_lowpoly_20261010_01':raise RuntimeError('Unexpected scene')
    root=bpy.data.collections['DISPLAY_NONAUTHORITATIVE']
    audit=collection2('AUDIT',root)
    audit['original_audit_json']=bpy.data.collections['RPI_AUDIT']['baseline_documents_json']
    display_states={}
    for colname in ('DISPLAY_BUILDINGS','DISPLAY_SURFACE_LINES'):
        for obj in bpy.data.collections[colname].all_objects:
            display_states[obj.name]=object_state(obj)
    audit['display_baseline_json']=json.dumps(display_states,sort_keys=True)
    audit['initial_validation_json']=json.dumps(initial,sort_keys=True)
    pavement=collection2('PAVEMENT',root);details=collection2('LANDMARKS',root)
    annotations=collection2('ANNOTATIONS',root)
    asphalt=material2('asphalt',(0.19,0.23,0.24));walk=material2('walks',(0.86,0.75,0.54))
    stair=material2('stairs',(0.60,0.29,0.12));ticks=material2('stair_ticks',(0.98,0.87,0.65))
    concrete=material2('concrete',(0.65,0.64,0.55));granite=material2('granite',(0.57,0.59,0.55))
    slate=material2('slate',(0.13,0.19,0.20));glass=material2('glazing',(0.22,0.44,0.47))
    darkglass=material2('window_insets',(0.085,0.17,0.19));trim=material2('warm_trim',(0.83,0.80,0.68))
    cedar=material2('cedar',(0.67,0.34,0.13));ink=material2('ink',(0.045,0.075,0.08),True)
    paper=material2('label_paper',(0.89,0.86,0.75),True)
    for old in sorted(bpy.data.collections['DISPLAY_SURFACE_LINES'].objects,key=object_name):
        old.hide_render=True;old.hide_viewport=True
        width=old['display_width_m'];half=width/2
        points=[Vector(p.co[:3]) for p in old.data.splines[0].points]
        verts=[]
        for i,p in enumerate(points):
            prev=points[max(0,i-1)];nxt=points[min(len(points)-1,i+1)]
            a=Vector((p.x-prev.x,p.y-prev.y));b=Vector((nxt.x-p.x,nxt.y-p.y))
            if a.length<1e-8:a=b.copy()
            if b.length<1e-8:b=a.copy()
            if a.length<1e-8:raise RuntimeError('Degenerate display station')
            a.normalize();b.normalize();na=Vector((-a.y,a.x));nb=Vector((-b.y,b.x));normal=na+nb
            if normal.length<1e-6:normal=nb.copy()
            normal.normalize();offset=normal*min(half/max(0.2,normal.dot(nb)),1.5*half)
            for x,y in ((p.x+offset.x,p.y+offset.y),(p.x,p.y),(p.x-offset.x,p.y-offset.y)):
                verts.append((x,y,terrain2(x,y)+0.10))
        faces=[]
        for i in range(len(points)-1):
            j=i*3
            faces.extend([(j,j+3,j+4),(j,j+4,j+1),(j+1,j+4,j+5),(j+1,j+5,j+2)])
        source=bpy.data.objects['GIS_'+old['source_id'].replace('/','_')]
        layers=json.loads(source['layers_json'])
        cat='roads' if 'roads' in layers else 'stairs' if 'stairs' in layers else 'paths'
        obj=mesh2('RIBBON_'+old['source_id'].replace('/','_'),verts,faces,pavement,asphalt if cat=='roads' else stair if cat=='stairs' else walk)
        obj['source_id']=old['source_id'];obj['display_width_m']=width
        obj['width_status']=old['width_status'];obj['centerline_original_object']=old.name
        obj['elevation_status']='Interpolated on unchanged 4 m presentation terrain + 0.10 m, not measured pavement elevation'
        if cat=='stairs':
            # Light crossbars are a stair symbol, not an invented count of physical treads.
            tv=[];tf=[]
            for i in range(1,len(points)-1,2):
                l=Vector(verts[3*i]);r=Vector(verts[3*i+2]);t=points[i+1]-points[i-1];t.z=0
                if t.length<1e-6:continue
                t.normalize();t*=0.13;start=len(tv)
                tv.extend([tuple(l-t+Vector((0,0,0.025))),tuple(r-t+Vector((0,0,0.025))),tuple(r+t+Vector((0,0,0.025))),tuple(l+t+Vector((0,0,0.025)))])
                tf.append((start,start+1,start+2,start+3))
            mark=mesh2('STAIR_SYMBOL_'+old['source_id'].replace('/','_'),tv,tf,pavement,ticks)
            mark['source_id']=old['source_id'];mark['meaning']='Cartographic stair hatch; not measured treads or step count'
    for key in sorted(LANDMARKS):
        info=LANDMARKS[key];old=bpy.data.objects['VIS_'+key.replace('/','_')]
        kind=info['kind'];xy=info['footprint_xy'];base=info['base_m'];roof=info['roof_base_m'];height=roof-base
        old.data.materials[0]=granite if kind=='chapel' else concrete if kind=='library' else glass
        old.data.materials[1]=slate if kind=='chapel' else concrete
        if info['faces']:
            roofobj=mesh2('ROOF_'+key.replace('/','_'),info['vertices'],info['faces'],details,slate if kind=='chapel' else concrete)
            roofobj['source_id']=key;roofobj['reference_url']=info['reference'];roofobj['dimensions_status']=info['dimensions_status']
        # Facade marks lie on the unchanged footprint wall planes, no horizontal offsets.
        verts=[];faces=[]
        for a,b in zip(xy,xy[1:]+xy[:1]):
            dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
            if length<3:continue
            if kind=='library':
                for frac in (0.28,0.52,0.76):
                    z=base+height*frac;start=len(verts)
                    verts.extend([(a[0],a[1],z),(b[0],b[1],z),(b[0],b[1],z+height*0.10),(a[0],a[1],z+height*0.10)])
                    faces.append((start,start+1,start+2,start+3))
            elif kind=='chapel':
                bays=max(1,int(length/6.5))
                for j in range(bays):
                    center=(j+0.5)/bays;w=min(1.25/length,0.3/bays);start=len(verts)
                    for t,z in ((center-w,base+height*.32),(center+w,base+height*.32),(center+w,base+height*.72),(center,base+height*.86),(center-w,base+height*.72)):
                        verts.append((a[0]+dx*t,a[1]+dy*t,z))
                    faces.append(tuple(range(start,start+5)))
            else:
                bays=max(1,int(length/5))
                for j in range(1,bays):
                    center=j/bays;w=.16/length;start=len(verts)
                    verts.extend([(a[0]+dx*(center-w),a[1]+dy*(center-w),base),(a[0]+dx*(center+w),a[1]+dy*(center+w),base),(a[0]+dx*(center+w),a[1]+dy*(center+w),roof),(a[0]+dx*(center-w),a[1]+dy*(center-w),roof)])
                    faces.append((start,start+1,start+2,start+3))
        facade=mesh2('FACADE_'+key.replace('/','_'),verts,faces,details,trim if kind=='empac' else darkglass)
        if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(xy,xy[1:]+xy[:1]))<0:
            facade.data.flip_normals()
        # Small normal render offset avoids coplanar flicker without moving vertices.
        facade['source_id']=key;facade['reference_url']=info['reference'];facade['dimensions_status']=info['dimensions_status']
        # Shader displacement is deliberately avoided. Wall-plane polygons use a minimal solidify shell.
        mod=facade.modifiers.new('Presentation surface relief 0.025m','SOLIDIFY');mod.thickness=.025;mod.offset=1
    # EMPAC wood motif follows the existing southern facade segments. This is
    # a reference-inspired graphic, not a surveyed interior hall or an entrance.
    emp=LANDMARKS['osm/way/262004862'];xy=emp['footprint_xy']
    segments=list(zip(xy[14:19],xy[15:20]));total=sum(math.dist(a,b) for a,b in segments)
    distance=0;vs=[];faces=[];center=emp['base_m']+(emp['roof_base_m']-emp['base_m'])*.56
    for a,b in segments:
        length=math.dist(a,b)
        for j in range(4):
            s0=distance+length*j/4;s1=distance+length*(j+1)/4
            lo=max(s0,total*.10);hi=min(s1,total*.90)
            if hi<=lo:continue
            start=len(vs)
            for s,sign in ((lo,-1),(hi,-1),(hi,1),(lo,1)):
                t=(s-distance)/length;u=(s/total-.5)/.4
                height=(emp['roof_base_m']-emp['base_m'])*.32*math.sqrt(max(0,1-u*u))
                vs.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,center+sign*height))
            faces.append((start,start+1,start+2,start+3))
        distance+=length
    wood=mesh2('EMPAC_CEDAR_CUE',vs,faces,details,cedar)
    if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(xy,xy[1:]+xy[:1]))<0:
        wood.data.flip_normals()
    wood['source_id']='osm/way/262004862';wood['dimensions_status']='Broad cedar-hull facade motif; interior location and dimensions are unverified'
    mod=wood.modifiers.new('Presentation surface relief 0.015m','SOLIDIFY');mod.thickness=.015;mod.offset=1
    # Copy the overview camera; retain the complete original camera and full-extent scene data.
    oldcam=scene.camera;camera=oldcam.copy();camera.data=oldcam.data.copy();camera.name=RUN2+'_Camera';annotations.objects.link(camera)
    building_vertices=[o.matrix_world@v.co for o in bpy.data.collections['DISPLAY_BUILDINGS'].objects for v in o.data.vertices]
    lo=Vector((min(v.x for v in building_vertices),min(v.y for v in building_vertices),0))
    hi=Vector((max(v.x for v in building_vertices),max(v.y for v in building_vertices),0))
    target=(lo+hi)/2;target.z=75
    camera.location=target+Vector((100,-560,860));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=1030;scene.camera=camera
    bpy.context.view_layer.update()
    for obj in bpy.data.collections['DISPLAY_PRESENTATION'].objects:
        if obj.type=='FONT':obj.hide_render=True;obj.hide_viewport=True
    scene.render.resolution_x=2100;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
    scene.cycles.samples=48;scene.cycles.use_denoising=True
    text2('TITLE','RPI / CAMPUS LANDMARKS',-475,321,19,annotations,ink,camera)
    text2('SUBTITLE','A low-poly study  /  Preserved GIS geometry',-475,301,8,annotations,ink,camera)
    text2('LEGEND','PALE: WALKWAYS    CHARCOAL: ROADS    HATCHED: STAIRS',-475,-309,8,annotations,ink,camera)
    text2('LIMITATIONS','Illustrative widths, heights and landmark details. Accessibility remains unverified.',-475,-325,8,annotations,ink,camera)
    text2('CREDIT','\u00a9 OpenStreetMap contributors / USGS 3DEP  |  openstreetmap.org/copyright',-475,-340,8,annotations,ink,camera)
    labels=[('Experimental Media and Performing Arts Center (EMPAC)','EMPAC'),('Folsom Library','FOLSOM LIBRARY'),
            ('Voorhees Computing Center','VCC / CHAPEL'),('Greene Building','GREENE'),('Amos Eaton Hall','AMOS EATON'),
            ('Darrin Communications Center','DCC'),('J Erik Jonsson Engineering Center','JEC'),('Rensselaer Student Union','STUDENT UNION')]
    inv=camera.matrix_world.inverted();used=[];label_records=[]
    for full,short in labels:
        obj=None
        for candidate in bpy.data.collections['DISPLAY_BUILDINGS'].objects:
            if candidate.get('source_name')==full:obj=candidate
        if obj is None:raise RuntimeError('Missing label building '+full)
        vs=[obj.matrix_world@v.co for v in obj.data.vertices];anchor=sum(vs,Vector())/len(vs);anchor.z=max(v.z for v in vs)+8
        projected=inv@anchor;w=len(short)*4.6+10;h=13
        x=projected.x-w/2;y=projected.y+14
        for shift in (0,18,36,54,-30,-48,72):
            test=(x,y+shift,x+w,y+shift+h)
            overlap=False
            for rect in used:
                if test[0]<rect[2]+5 and test[2]>rect[0]-5 and test[1]<rect[3]+5 and test[3]>rect[1]-5:overlap=True
            if not overlap: y+=shift;break
        used.append((x,y,x+w,y+h))
        backing=mesh2('LABEL_BG_'+short,[(x-3,y-2,-91),(x+w,y-2,-91),(x+w,y+h,-91),(x-3,y+h,-91)],[(0,1,2,3)],annotations,paper);backing.parent=camera;backing.visible_shadow=False
        text2('LABEL_'+short,short,x+2,y+1,8,annotations,ink,camera)
        leader=line2('LEADER_'+short,[(projected.x,projected.y,-90.5),(x+w/2,y-2,-90.5)],.32,annotations,ink);leader.parent=camera;leader.visible_shadow=False
        label_records.append({'source_id':obj['source_id'],'text':short,'box':used[-1]})
    # Project grid north; no claim that screen-up equals north.
    direction=camera.matrix_world.to_quaternion().inverted()@Vector((0,1,0));direction.z=0;direction.normalize()
    start=Vector((440,290,-90));end=start+direction*26
    arrow=line2('NORTH',[tuple(start),tuple(end)],.65,annotations,ink);arrow.parent=camera;arrow.visible_shadow=False
    side=Vector((-direction.y,direction.x,0))
    head=mesh2('NORTH_HEAD',[tuple(end),tuple(end-direction*8+side*3),tuple(end-direction*8-side*3)],[(0,1,2)],annotations,ink);head.parent=camera;head.visible_shadow=False
    text2('NORTH_TEXT','GRID N',420,326,7,annotations,ink,camera)
    audit['label_layout_json']=json.dumps(label_records,sort_keys=True)
    audit['landmark_parameters_json']=json.dumps(LANDMARKS,sort_keys=True)
    audit['checkpoint']=checkpoint
    scene['pass02_notes']='Flat display ribbons retain exact centerline XY and illustrative widths. Three reference-inspired landmarks; sourced building labels. No GIS topology edits.'
    bpy.context.view_layer.update()
    print(json.dumps({'checkpoint':checkpoint,'ribbons':len([o for o in pavement.objects if 'RIBBON_' in o.name]),'landmarks':3,'labels':len(labels),'branch':'codex/pilot-landmarks-pavement-pass02'}))

def validate_pass02():
    report=original_validation();errors=report['errors'];audit=bpy.data.collections[RUN2+'_AUDIT']
    if audit['original_audit_json']!=bpy.data.collections['RPI_AUDIT']['baseline_documents_json']:errors.append('Original saved audit changed')
    before=json.loads(audit['display_baseline_json'])
    for name,state in before.items():
        current=json.loads(json.dumps(object_state(bpy.data.objects[name])))
        # Only original line visibility differs. Building material slots change, not faces/indices.
        for field in ('hide_render','hide_viewport'):current[field]=state[field]
        if current!=state:errors.append('Original display geometry/metadata changed '+name)
    max_center_error=0;max_ground_error=0;ribbons=0;station_count=0
    for obj in bpy.data.collections[RUN2+'_PAVEMENT'].objects:
        if 'centerline_original_object' not in obj:continue
        ribbons+=1;old=bpy.data.objects[obj['centerline_original_object']]
        points=old.data.splines[0].points
        if len(obj.data.vertices)!=3*len(points):errors.append('Ribbon station count '+obj.name);continue
        if len(obj.data.polygons)!=4*(len(points)-1):errors.append('Ribbon face count '+obj.name)
        if obj['source_id']!=old['source_id'] or obj['display_width_m']!=old['display_width_m']:errors.append('Ribbon source/width changed '+obj.name)
        for i,p in enumerate(points):
            v=obj.data.vertices[3*i+1].co;err=max(abs(v.x-p.co.x),abs(v.y-p.co.y));max_center_error=max(max_center_error,err);station_count+=1
        for v in obj.data.vertices:
            err=abs(v.co.z-terrain2(v.co.x,v.co.y)-.10);max_ground_error=max(max_ground_error,err)
    if max_center_error>1e-5:errors.append('Ribbon centerline XY tolerance exceeded')
    if max_ground_error>.0002:errors.append('Ribbon terrain conformance tolerance exceeded')
    if ribbons!=316:errors.append('Surface feature count changed')
    labels=json.loads(audit['label_layout_json'])
    for i,a in enumerate(labels):
        for b in labels[i+1:]:
            x=a['box'];y=b['box']
            if x[0]<y[2] and x[2]>y[0] and x[1]<y[3] and x[3]>y[1]:errors.append('Label collision')
    report.update(passed=not errors,original_display_objects_compared=len(before),ribbons=ribbons,centerline_stations=station_count,
        max_centerline_xy_error_m=max_center_error,max_pavement_terrain_error_m=max_ground_error,
        labels=len(labels),landmarks=3,source_widths_inferred=False,
        limitations=['All existing illustrative widths retained; no measured pavement edges added.',
        'Roof rise, window bays, facade details and heights are illustrative.',
        'No route graph connectivity, accessibility or source elevation inferred.',
        'Original full-extent camera and 32 omitted multilevel/indoor source lines retained.'])
    audit['validation_json']=json.dumps(report,sort_keys=True)
    print(json.dumps(report))
    if errors:raise RuntimeError('Pass 02 validation failed')
    return report
