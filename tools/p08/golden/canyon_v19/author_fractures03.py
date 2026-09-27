"""Far33-44 closed terraced composition study; fixed V18-02 camera/road/near geometry."""
import bpy,bmesh,json,math
from array import array
from mathutils import Vector,noise
ROOT='D:/Project/Unity/racing-bois/'
SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_02.blend'
DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_03.blend'
if bpy.data.filepath.replace('\\','/')!=SOURCE:
    raise RuntimeError('Load owned frozen V19-02 separately before authoring.')
scene=bpy.context.scene
material=bpy.data.materials['Canyon_Sandstone']
target_names=['Canyon_L%d_Far_%02d'%(level,index) for index in range(33,45) for level in range(3)]
if any(bpy.data.objects.get(name) is None or bpy.data.objects[name].data.users!=1 for name in target_names):
    raise RuntimeError('Expected36 independently owned Far meshes.')
def values(collection,property_name,count,type_code):
    result=array(type_code,[0])*count
    collection.foreach_get(property_name,result)
    return result

def identity(obj):
    mesh=obj.data
    return (values(mesh.vertices,'co',len(mesh.vertices)*3,'f'),
        values(mesh.loops,'vertex_index',len(mesh.loops),'i'),
        values(mesh.polygons,'loop_start',len(mesh.polygons),'i'),
        values(mesh.polygons,'loop_total',len(mesh.polygons),'i'),
        values(mesh.polygons,'material_index',len(mesh.polygons),'i'),
        [values(layer.data,'uv',len(mesh.loops)*2,'f') for layer in mesh.uv_layers],
        [m.name for m in mesh.materials],[list(row) for row in obj.matrix_world],obj.hide_render,obj.hide_get())

def fixed_scene_state():
    camera=scene.camera
    lights=[]
    for obj in scene.objects:
        if obj.type=='LIGHT':
            lights.append((obj.name,[list(row) for row in obj.matrix_world],obj.data.type,obj.data.energy,list(obj.data.color)))
    nodes=[]
    if scene.world and scene.world.use_nodes:
        for node in scene.world.node_tree.nodes:
            inputs=[]
            for socket in node.inputs:
                if socket.type in {'VALUE','INT','BOOLEAN'}:
                    inputs.append((socket.name,float(socket.default_value)))
                elif socket.type in {'VECTOR','RGBA'}:
                    inputs.append((socket.name,list(socket.default_value)))
            nodes.append((node.name,node.type,inputs,node.image.filepath if node.type=='TEX_ENVIRONMENT' and node.image else None))
    return {'cameraMatrix':[list(row) for row in camera.matrix_world],
        'lens':camera.data.lens,'sensorWidth':camera.data.sensor_width,'sensorFit':camera.data.sensor_fit,
        'clipStart':camera.data.clip_start,'clipEnd':camera.data.clip_end,
        'resolution':[scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage],
        'lights':lights,'worldNodes':nodes,'viewTransform':scene.view_settings.view_transform,
        'look':scene.view_settings.look,'exposure':scene.view_settings.exposure,'gamma':scene.view_settings.gamma}

outside={obj.name:identity(obj) for obj in scene.objects if obj.type=='MESH' and obj.name not in target_names}
fixed_before=fixed_scene_state()
states=[(obj,obj.hide_get(),obj.select_get()) for obj in bpy.context.view_layer.objects]
active=bpy.context.view_layer.objects.active
materials_before=set(bpy.data.materials);images_before=set(bpy.data.images)
# index, upper-front X/Y, cliff length, front-normal angle, nominal summit,
# buried base, real rear depth, horizontal segments, vertical segments.
layout=[
 (33,-88,275,150,0,66,-44,48,112,62),
 (34,-72,385,155,-5,82,-48,50,112,64),
 (35,-55,500,160,-12,90,-52,52,108,62),
 (36,-32,625,165,-22,89,-56,54,96,58),
 (37,-6,750,170,-35,84,-60,56,88,54),
 (38,24,875,175,-50,75,-64,60,84,50),
 (39,55,1000,180,-65,69,-68,64,76,46),
 (40,92,1125,185,-80,62,-70,66,72,44),
 (41,130,1235,190,-90,54,-72,68,68,42),
 (42,170,1330,200,-90,48,-74,70,64,40),
 (43,215,1440,210,-95,44,-76,72,60,38),
 (44,275,1525,260,-110,42,-80,85,64,38)]

def smooth(a,b,value):
    t=max(0,min(1,(value-a)/(b-a)))
    return t*t*(3-2*t)

def random_unit(index,seed):
    value=math.sin(index*127.1+seed*311.7)*43758.5453
    return value-math.floor(value)

def plan(theta,rx,ry):
    c,s=math.cos(theta),math.sin(theta)
    return Vector(((1 if c>=0 else -1)*abs(c)**.82*rx,
                   (1 if s>=0 else -1)*abs(s)**.82*ry,0))

def append_butte(points,faces,center,rx,ry,bottom,top,angle,segments,vertical,seed,kind):
    n=Vector((math.cos(angle),math.sin(angle),0));along=Vector((-n.y,n.x,0))
    # Physical arc-length coordinates avoid a fixed small joint count around
    # huge masses. Each joint interval is explicitly 3 to 10 metres.
    arc=[0.0];previous=plan(0,rx,ry)
    for column in range(1,segments+1):
        point=plan(2*math.pi*column/segments,rx,ry)
        arc.append(arc[-1]+(point-previous).length);previous=point
    perimeter=arc[-1]
    joints=[0.0];joint_index=0
    while joints[-1]<perimeter:
        joints.append(joints[-1]+4+5*random_unit(joint_index,seed));joint_index+=1
    # Redistribute only the final short remainder by uniform scaling. Record
    # the actual resulting spacings instead of claiming an idealised range.
    factor=perimeter/joints[-1];joints=[value*factor for value in joints]
    spacing=[joints[i+1]-joints[i] for i in range(len(joints)-1)]
    surface_records.append({'seed':seed,'kind':kind,'perimeterMetres':perimeter,
        'jointCount':len(spacing),'minimumJointSpacingMetres':min(spacing),
        'maximumJointSpacingMetres':max(spacing),'angularSegments':segments,
        'maximumSurfaceArcStepMetres':max(arc[i+1]-arc[i] for i in range(segments))})
    rings=[]
    for row in range(vertical+1):
        t=row/vertical;ring=[]
        for column in range(segments):
            theta=2*math.pi*column/segments;u=arc[column]
            p=plan(theta,rx,ry);c,s=math.cos(theta),math.sin(theta)
            # Several nonperiodic scales shape the skyline and large setbacks.
            broad=noise.noise(Vector((p.x*.028+seed,p.y*.028-seed,seed*.37)))
            medium=noise.noise(Vector((p.x*.09,p.y*.09,seed)))
            highest=top+5.8*broad+2.7*medium+1.4*math.sin(theta*3.1+seed)
            z=bottom+(highest-bottom)*t
            if kind=='base':
                # Continuous sloping talus below the upper ledge. This replaces
                # the prior tall, nearly vertical blank cylinder.
                scale=.73
                outward=108*(1-t)**1.35
                cliff_weight=smooth(.72,.94,t)
            elif kind=='spur':
                scale=.79-.08*smooth(.68,.77,t)
                outward=44*(1-t)**1.3
                cliff_weight=.3+.7*smooth(.5,.8,t)
            else:
                scale=1-.10*t-.07*smooth(.28,.36,t)-.09*smooth(.68,.75,t)
                outward=0.0;cliff_weight=1.0
            # Deep, irregular 15–35m setbacks coexist with physically smaller
            # rock faces. Relief is metre-scale geometry, not a texture claim.
            radial=Vector((p.x,p.y,0)).normalized()
            relief=4.2*broad+2.7*medium
            warped=(u+.45*math.sin(z*.23+seed)+.65*noise.noise(Vector((u*.08,z*.1,seed))))%perimeter
            joint=0
            while joint+1<len(joints)-1 and joints[joint+1]<warped:joint+=1
            left=warped-joints[joint];right=joints[joint+1]-warped
            distance=min(left,right)
            depth=1.7+2.3*random_unit(joint+17,seed)
            width=.58+.68*random_unit(joint+39,seed)
            # Tapered V cuts have sloped sidewalls and remain visible at the
            # comparison distance. Broken joints terminate at varying beds.
            activity=.45+.55*smooth(.02,.24,t)
            crack=depth*max(0,1-distance/width)*activity
            bed_spacing=4.8+2.8*random_unit(8,seed)
            phase=z+1.6*noise.noise(Vector((u*.045,seed,0)))+.8*math.sin(u*.07+seed)
            bed_distance=abs((phase+1000)%bed_spacing-bed_spacing*.5)
            bedding=(1.15+.75*medium)*max(0,1-bed_distance/1.15)
            fine=.9*noise.noise(Vector((p.x*.38,p.y*.38,z*.41+seed)))
            relief+=(fine-crack-bedding)*cliff_weight
            px=p.x*scale+radial.x*(outward+relief)
            py=p.y*scale+radial.y*(outward+relief)
            point=Vector(center)+along*px+n*py;point.z=z
            ring.append(len(points));points.append(point)
        rings.append(ring)
    for row in range(vertical):
        for column in range(segments):
            nxt=(column+1)%segments
            faces.append((rings[row][column],rings[row][nxt],rings[row+1][nxt],rings[row+1][column]))
    bottom_center=len(points);points.append(Vector((center[0],center[1],bottom)))
    top_center=len(points);points.append(Vector((center[0],center[1],top-.25)))
    for column in range(segments):
        nxt=(column+1)%segments
        faces.append((bottom_center,rings[0][nxt],rings[0][column]))
        faces.append((top_center,rings[-1][column],rings[-1][nxt]))

surface_records=[]

def build_terraced_mass(spec,obj):
    index,ax,ay,length,degrees,nominal,bottom,rear,columns,vertical=spec
    seed=index*1.17;angle=math.radians(degrees)
    n=Vector((math.cos(angle),math.sin(angle),0));along=Vector((-n.y,n.x,0));anchor=Vector((ax,ay,0))
    points=[];faces=[]
    segments=640 if index<=36 else 448
    levels=90 if index<=36 else 72
    base_center=anchor-n*20
    append_butte(points,faces,base_center,length*.81,95 if index<=37 else 86,min(bottom,-82),nominal-36,
                 angle+.08*math.sin(seed),segments,levels,seed,'base')
    for offset,height_delta,height,phase in [(-.21,0,41,2.1),(.22,10,38,4.3)]:
        center=anchor+along*(length*offset)-n*26
        append_butte(points,faces,center,length*.27,32 if index<=37 else 29,nominal-height_delta-height,nominal-height_delta,
                     angle+.18*math.sin(seed+phase),384 if index<=36 else 256,48 if index<=36 else 40,seed+phase,'upper')
    spur_center=base_center+n*52+along*(length*.11*math.sin(seed))
    append_butte(points,faces,spur_center,length*.26,34,min(bottom,-65),nominal-43,
                 angle-.21*math.sin(seed),384 if index<=36 else 256,levels,seed+6.7,'spur')
    inverse=obj.matrix_world.inverted()
    mesh=bpy.data.meshes.new('Canyon_Far%02d_PhysicalFractures_V19_03_L0'%index)
    mesh.from_pydata([inverse@point for point in points],[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    remaining=set(bm.faces)
    while remaining:
        seed_face=remaining.pop();component=[seed_face];stack=[seed_face]
        while stack:
            face=stack.pop()
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in remaining:remaining.remove(linked);component.append(linked);stack.append(linked)
        volume=0.0
        for face in component:
            a,b,c=[vertex.co for vertex in face.verts];volume+=a.dot(b.cross(c))/6
        if volume<0:
            for face in component:face.normal_flip()
    bm.to_mesh(mesh);bm.free();mesh.update();mesh.materials.append(material)
    for polygon in mesh.polygons:polygon.use_smooth=False
    return mesh
def map_and_audit(obj):
    mesh=obj.data
    mesh.calc_loop_triangles()
    layer=mesh.uv_layers.new(name='UV0_SurfaceMetres') if not mesh.uv_layers else mesh.uv_layers[0]
    for polygon in mesh.polygons:
        if polygon.loop_total!=3:
            raise RuntimeError('Expected triangulated authored surface.')
        points=[obj.matrix_world@mesh.vertices[mesh.loops[index].vertex_index].co for index in polygon.loop_indices]
        normal=(points[1]-points[0]).cross(points[2]-points[0])
        axis=0 if abs(normal.x)>=abs(normal.y) and abs(normal.x)>=abs(normal.z) else 1 if abs(normal.y)>=abs(normal.z) else 2
        for index,point in zip(polygon.loop_indices,points):
            layer.data[index].uv=(point.y/2.4,point.z/2.4) if axis==0 else (point.x/2.4,point.z/2.4) if axis==1 else (point.x/2.4,point.y/2.4)
    mesh.update();mesh.calc_loop_triangles()
    bm=bmesh.new();bm.from_mesh(mesh)
    boundary=sum(1 for edge in bm.edges if edge.is_boundary)
    nonmanifold=sum(1 for edge in bm.edges if not edge.is_manifold)
    volume=bm.calc_volume(signed=True);bm.free()
    if boundary or nonmanifold or volume<=0:
        raise RuntimeError('Authored closed-volume invariant failed: '+obj.name)
    uv_min=None;physical_min=None;seen=set();duplicates=0
    low=[float('inf')]*3;high=[float('-inf')]*3
    for vertex in mesh.vertices:
        point=obj.matrix_world@vertex.co
        for axis in range(3):low[axis]=min(low[axis],point[axis]);high[axis]=max(high[axis],point[axis])
    for triangle in mesh.loop_triangles:
        key=tuple(sorted(triangle.vertices))
        if key in seen:duplicates+=1
        seen.add(key)
        a,b,c=[mesh.vertices[index].co for index in triangle.vertices]
        physical=(obj.matrix_world.to_3x3()@(b-a)).cross(obj.matrix_world.to_3x3()@(c-a)).length_squared
        uv=[layer.data[index].uv for index in triangle.loops]
        cross=(float(uv[1].x)-uv[0].x)*(float(uv[2].y)-uv[0].y)-(float(uv[1].y)-uv[0].y)*(float(uv[2].x)-uv[0].x)
        if not math.isfinite(physical) or physical<=1e-16 or not math.isfinite(cross) or abs(cross)<=1e-14:
            raise RuntimeError('Physical/primary UV triangle threshold failed: '+obj.name)
        uv_min=abs(cross) if uv_min is None else min(uv_min,abs(cross))
        physical_min=physical if physical_min is None else min(physical_min,physical)
    if duplicates:raise RuntimeError('Duplicate authored triangles: '+obj.name)
    return {'object':obj.name,'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),
        'boundaryEdges':boundary,'nonManifoldEdges':nonmanifold,'signedVolumeCubicMetres':volume,
        'minimumPrimaryUvCross':uv_min,'minimumPhysicalCrossSquaredMetres':physical_min,
        'materials':[mat.name for mat in mesh.materials],'minimumBlender':low,'maximumBlender':high,
        'uvPolicy':'Physical world projection per triangle at2.4m/repeat; no epsilon UV offsets.'}

try:
    old_data=[];rows=[]
    for spec in layout:
        index=spec[0]
        targets=[bpy.data.objects['Canyon_L%d_Far_%02d'%(level,index)] for level in range(3)]
        old_data.extend(obj.data for obj in targets)
        primary=build_terraced_mass(spec,targets[0]);targets[0].data=primary
        for level,ratio in [(1,.44),(2,.17)]:
            obj=targets[level];mesh=primary.copy();mesh.name='Canyon_Far%02d_Terraced_V19_L%d'%(index,level)
            transform=obj.matrix_world.inverted()@targets[0].matrix_world
            for vertex in mesh.vertices:vertex.co=transform@vertex.co
            obj.data=mesh
            bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
            reduction=obj.modifiers.new('Terraced Far LOD','DECIMATE');reduction.ratio=ratio;reduction.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=reduction.name)
        module_rows=[map_and_audit(obj) for obj in targets]
        if not module_rows[0]['triangles']>module_rows[1]['triangles']>module_rows[2]['triangles']:
            raise RuntimeError('LOD counts do not decrease.')
        rows.extend(module_rows)
    for obj,hidden,selected in states:obj.hide_set(hidden);obj.select_set(selected)
    bpy.context.view_layer.objects.active=active
    for name,before in outside.items():
        if identity(bpy.data.objects[name])!=before:raise RuntimeError('Outside Far chain changed: '+name)
    if fixed_scene_state()!=fixed_before or set(bpy.data.materials)!=materials_before or set(bpy.data.images)!=images_before:
        raise RuntimeError('Frozen camera/light/material/image state changed.')
    for mesh in old_data:
        if mesh.users!=0:raise RuntimeError('Unexpected shared old Far mesh.')
        bpy.data.meshes.remove(mesh)
    totals=[0,0,0]
    for obj in bpy.data.objects['RB_Golden_Canyon'].children_recursive:
        if obj.type!='MESH':continue
        for level in range(3):
            if '_L%d_'%level in obj.name:
                obj.data.calc_loop_triangles();totals[level]+=len(obj.data.loop_triangles)
    scene.render.filepath=ROOT+'docs/p08/golden/canyon/v19/candidate03-gameplay.png'
    scene['v19_scope']='Unaccepted Far33-44 fractured closed mesas and sloping talus; fixedV18-02camera/road/nearcliff. NoAssets export.'
    scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_02.blend'
    bpy.ops.wm.save_as_mainfile(filepath=DESTINATION,check_existing=False)
    print('CANYON_V19_FRACTURES03 '+json.dumps({'source':DESTINATION,'parentSource':SOURCE,'changedObjects':target_names,
        'layout':layout,'physicalSurfaces':surface_records,'audit':rows,'sceneLodTriangles':totals,'otherSceneMeshesExactlyUnchanged':len(outside),
        'cameraAndLightingExactlyUnchanged':True,'materialAndImageMembershipUnchanged':True,
        'fixedScene':fixed_before,'visualAccepted':False,'exportedToAssets':False}))
except Exception:
    bpy.ops.wm.open_mainfile(filepath=SOURCE)
    raise
