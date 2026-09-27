"""One authored closed sandstone mass; only Far33 LOD0/1/2 change from frozen05."""
import bpy, bmesh, json, math
from array import array
from mathutils import Vector, noise

ROOT='D:/Project/Unity/racing-bois/'
SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_05.blend'
DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V18/RB_Golden_Canyon_V18_01.blend'
if bpy.data.filepath.replace('\\','/')!=SOURCE:
    raise RuntimeError('Expected owned frozen05; do not modify another source.')
scene=bpy.context.scene
target_names=['Canyon_L%d_Far_33'%level for level in range(3)]
targets=[bpy.data.objects.get(name) for name in target_names]
if any(obj is None or obj.type!='MESH' or obj.data.users!=1 for obj in targets):
    raise RuntimeError('Expected three independently owned Far33 meshes.')
material=bpy.data.materials.get('Canyon_Sandstone')
if material is None:
    raise RuntimeError('Existing sandstone material missing; no new material is generated.')

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
materials_before=set(bpy.data.materials)
images_before=set(bpy.data.images)

def smooth(a,b,value):
    t=max(0,min(1,(value-a)/(b-a)))
    return t*t*(3-2*t)

def top_height(u):
    return 74+3.8*math.sin(u*.041+.6)+2.2*math.sin(u*.143+1.3)+1.15*noise.noise(Vector((u*.37,3.7,1.2)))

def front_x(u,z):
    # The visible front faces east (+X), toward the road/camera and the sunset.
    # Its terraces retreat into real rock volume as height increases, rather
    # than retaining the long cut shelf of a stretched scan.
    retreat=2.0*smooth(-25,5,z)
    retreat+=3.4*smooth(7+2.8*math.sin(u*.081),9+2.8*math.sin(u*.081),z)
    retreat+=5.2*smooth(34+4*math.sin(u*.073+1.2),36+4*math.sin(u*.073+1.2),z)
    retreat+=6.8*smooth(59+3.3*math.sin(u*.099+.8),61+3.3*math.sin(u*.099+.8),z)
    shifted=u+.65*math.sin(z*.079)+.25*math.sin(z*.27)
    joints=[-91,-80,-68,-59,-47,-36,-24,-13,-3,9,20,33,43,54,67,78,90]
    joint_distance=min(abs(shifted-joint) for joint in joints)
    vertical_crack=2.15*math.exp(-(joint_distance/.82)**2)+.35*math.exp(-(joint_distance/1.6)**2)
    phase=z+.65*math.sin(u*.083)+.35*math.sin(u*.217)
    beds=[-72,-49,-29,-14,-2,8,17,27,37,47,57,66,74]
    bed_distance=min(abs(phase-bed) for bed in beds)
    bedding=1.15*math.exp(-(bed_distance/.62)**2)
    column=int((u+100)/10.7)
    row=int((phase+100)/9.1)
    block=.68*math.sin(column*5.73+row*3.11)
    erosion=.26*noise.noise(Vector((u*.25,z*.15,8.2)))+.10*noise.noise(Vector((u*.91,z*.77,2.9)))
    return -78-retreat-vertical_crack-bedding-block-erosion

def build_mass():
    points=[];faces=[];front=[];back_bottom=[];back_top=[]
    columns=154
    for column in range(columns+1):
        u=-92.5+185*column/columns
        highest=top_height(u)
        heights=[-100,-75,-50,-30,-20]+[-20+(highest+20)*step/80 for step in range(1,81)]
        indices=[]
        for z in heights:
            x=front_x(u,z)
            if x<=-143:
                raise RuntimeError('Authored front intersects its rear volume.')
            indices.append(len(points));points.append((x,260+u,z))
        front.append(indices)
        back_bottom.append(len(points));points.append((-148,260+u,-100))
        back_top.append(len(points));points.append((-148,260+u,highest-2+.5*noise.noise(Vector((u*.17,8.1,6.2)))))
    rows=len(front[0])
    for column in range(columns):
        for level in range(rows-1):
            faces.append((front[column][level],front[column+1][level],front[column+1][level+1],front[column][level+1]))
        faces.append((front[column][-1],front[column+1][-1],back_top[column+1],back_top[column]))
        faces.append((front[column][0],back_bottom[column],back_bottom[column+1],front[column+1][0]))
        faces.append((back_bottom[column],back_top[column],back_top[column+1],back_bottom[column+1]))
    faces.append(tuple(front[0]+[back_top[0],back_bottom[0]]))
    faces.append(tuple(list(reversed(front[-1]))+[back_bottom[-1],back_top[-1]]))
    inverse=targets[0].matrix_world.inverted()
    mesh=bpy.data.meshes.new('Canyon_Far33_AuthoredMass_V18_L0')
    mesh.from_pydata([inverse@Vector(point) for point in points],[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:
        for face in bm.faces:face.normal_flip()
    bm.to_mesh(mesh);bm.free();mesh.update()
    mesh.materials.append(material)
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
    old_data=[obj.data for obj in targets]
    primary=build_mass()
    targets[0].data=primary
    for level,ratio in [(1,.42),(2,.16)]:
        obj=targets[level]
        # Mesh coordinates are converted between the preserved object origins.
        mesh=primary.copy();mesh.name='Canyon_Far33_AuthoredMass_V18_L%d'%level
        transform=obj.matrix_world.inverted()@targets[0].matrix_world
        for vertex in mesh.vertices:vertex.co=transform@vertex.co
        obj.data=mesh
        bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
        reduction=obj.modifiers.new('Far33 authored mass LOD','DECIMATE')
        reduction.ratio=ratio;reduction.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=reduction.name)
    rows=[map_and_audit(obj) for obj in targets]
    if not rows[0]['triangles']>rows[1]['triangles']>rows[2]['triangles']:
        raise RuntimeError('Authored LOD triangle counts must decrease.')
    for obj,hidden,selected in states:
        obj.hide_set(hidden);obj.select_set(selected)
    bpy.context.view_layer.objects.active=active
    for name,before in outside.items():
        if identity(bpy.data.objects[name])!=before:
            raise RuntimeError('Mesh outside Far33 changed: '+name)
    if fixed_scene_state()!=fixed_before or set(bpy.data.materials)!=materials_before or set(bpy.data.images)!=images_before:
        raise RuntimeError('Frozen camera/lighting/material/image identity changed.')
    for mesh in old_data:
        if mesh.users!=0:raise RuntimeError('Old Far33 mesh unexpectedly shared.')
        bpy.data.meshes.remove(mesh)
    scene.render.filepath=ROOT+'docs/p08/golden/canyon/v18/candidate01-gameplay.png'
    scene['v18_scope']='Unaccepted Far33-only authored closed sandstone mass experiment; no Assets export.'
    scene['v18_parent_source_sha256']='b02ce427127da026540830c2043540c47292a14a2bd953618a4f6e5af3c95a78'
    bpy.ops.wm.save_as_mainfile(filepath=DESTINATION,check_existing=False)
    print('CANYON_V18_FAR33_01 '+json.dumps({'source':DESTINATION,'parentSource':SOURCE,
        'changedObjects':target_names,'audit':rows,'otherSceneMeshesExactlyUnchanged':len(outside),
        'cameraAndLightingExactlyUnchanged':True,'materialsAndImagesOutsideTargetUnchanged':True,
        'fixedScene':fixed_before,'surfacePolicy':'East-facing front toward road/camera, retreating irregular terraces and deep joints, closed rear volume; no whole-scan stretch.',
        'visualAccepted':False,'exportedToAssets':False}))
except Exception:
    bpy.ops.wm.open_mainfile(filepath=SOURCE)
    raise
