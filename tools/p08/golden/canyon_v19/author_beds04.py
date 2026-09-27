"""Far33-44 closed terraced composition study; fixed V18-02 camera/road/near geometry."""
import bpy,bmesh,json,math
from array import array
from mathutils import Vector,noise
ROOT='D:/Project/Unity/racing-bois/'
SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_03.blend'
DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_04.blend'
if bpy.data.filepath.replace('\\','/')!=SOURCE:
    raise RuntimeError('Load owned frozen V19-03 separately before authoring.')
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
    # A dense temporary plan lookup does not add mesh vertices. Mesh vertices
    # occur at fracture valleys/shoulders and explicit bed transitions only.
    lookup_count=2048;plan_points=[plan(2*math.pi*i/lookup_count,rx,ry) for i in range(lookup_count+1)]
    arc=[0.0]
    for i in range(lookup_count):arc.append(arc[-1]+(plan_points[i+1]-plan_points[i]).length)
    perimeter=arc[-1];joint_count=max(12,round(perimeter/7.0))
    height=top-bottom
    rock_start=max(bottom,-13+7*math.sin(seed)) if kind=='base' else bottom
    boundaries=[];level=rock_start+6.0+3*random_unit(6,seed)
    while level<top-3:
        boundaries.append(level);level+=6.0+5*random_unit(len(boundaries)+12,seed)
    row_z=[bottom,top]
    if rock_start>bottom+2:
        row_z.extend([bottom+(rock_start-bottom)*.32,bottom+(rock_start-bottom)*.67,rock_start])
    for boundary in boundaries:row_z.extend([boundary-.9,boundary+.9])
    row_z=sorted(set(row_z))
    joint_sets=[]
    for band in range(len(boundaries)+1):
        intervals=[4.5+4.5*random_unit(j,seed+band*1.67) for j in range(joint_count)]
        factor=perimeter/sum(intervals);positions=[0.0]
        for interval in intervals:positions.append(positions[-1]+interval*factor)
        joint_sets.append(positions)
    surface_records.append({'seed':seed,'kind':kind,'referencePlanPerimeterMetres':perimeter,
        'jointsPerBed':joint_count,'verticesPerRing':joint_count*4,'verticalRings':len(row_z),
        'bedHeightsMetres':boundaries,'rockStartMetres':rock_start,
        'sampling':'Vertices at fractured block shoulders and bed transitions; no uniform dense grid.'})
    rings=[]
    for row,nominal_z in enumerate(row_z):
        t=(nominal_z-bottom)/height;ring=[]
        band=0
        while band<len(boundaries) and nominal_z>boundaries[band]:band+=1
        positions=joint_sets[band]
        for joint in range(joint_count):
            interval=positions[joint+1]-positions[joint]
            for subdivision,fraction in enumerate([0,.15,.5,.85]):
                u=positions[joint]+interval*fraction
                low=0;high=lookup_count
                while high-low>1:
                    middle=(low+high)//2
                    if arc[middle]<=u:low=middle
                    else:high=middle
                blend=(u-arc[low])/(arc[high]-arc[low])
                p=plan_points[low].lerp(plan_points[high],blend)
                theta=2*math.pi*(low+blend)/lookup_count
                broad=noise.noise(Vector((p.x*.035+seed,p.y*.035-seed,seed*.37)))
                medium=noise.noise(Vector((p.x*.11,p.y*.11,seed+band*.53)))
                # Bedding tilts and terminates locally; the top is not a ring
                # copied uniformly around every neighbouring butte.
                top_break=4.3*broad+2.3*noise.noise(Vector((p.x*.12,p.y*.12,seed)))
                z=nominal_z+top_break*smooth(.45,1,t)+1.0*math.sin(u*.055+seed)*math.sin(t*math.pi)
                radial=p.normalized()
                if kind=='base':
                    talus_end=rock_start+8*math.sin(theta*2.7+seed)
                    foot=max(0,(talus_end-z)/max(1,talus_end-bottom))
                    lobe=.30+.70*max(0,math.sin(theta*3+seed))**2
                    outward=76*lobe*foot**1.25
                    scale=.77;cliff_weight=smooth(rock_start-4,rock_start+8,z)
                    relief=3.5*noise.noise(Vector((p.x*.045,p.y*.045,z*.05+seed)))
                    relief+=2.0*noise.noise(Vector((p.x*.12,p.y*.12,z*.15+seed)))
                else:
                    outward=7*(1-t)**1.4 if kind=='spur' else 0.0
                    scale=1-.035*t;cliff_weight=1.0
                    relief=2.3*broad+1.15*medium
                terrace=0.0
                for bed,boundary in enumerate(boundaries):
                    termination=noise.noise(Vector((u*.022+bed*2.1,seed,bed*.73)))
                    active=smooth(-.42,.10,termination)
                    terrace+=(1.8+2.7*random_unit(bed+35,seed))*active*smooth(boundary-.9,boundary+.9,nominal_z)
                # Joints change position in every bed. A finite valley joins
                # neighbouring angular block faces, rather than a continuous
                # sinusoidal rib repeated from foundation to summit.
                crack=(1.5+1.8*random_unit(joint+7,seed+band)) if subdivision==0 else 0.0
                block=(random_unit(joint+21,seed+band*1.67)-.5)*2.1
                relief+=(block-crack)*cliff_weight-terrace
                relief=max(relief,-p.length*.55)
                px=p.x*scale+radial.x*(outward+relief)
                py=p.y*scale+radial.y*(outward+relief)
                point=Vector(center)+along*px+n*py;point.z=z
                ring.append(len(points));points.append(point)
        rings.append(ring)
    count=joint_count*4
    for row in range(len(rings)-1):
        for column in range(count):
            nxt=(column+1)%count
            faces.append((rings[row][column],rings[row][nxt],rings[row+1][nxt],rings[row+1][column]))
    bottom_center=len(points);points.append(Vector((center[0],center[1],bottom)))
    top_center=len(points);points.append(Vector((center[0],center[1],top-.25)))
    for column in range(count):
        nxt=(column+1)%count
        faces.append((bottom_center,rings[0][nxt],rings[0][column]))
        faces.append((top_center,rings[-1][column],rings[-1][nxt]))

surface_records=[]

def build_terraced_mass(spec,obj):
    index,ax,ay,length,degrees,nominal,bottom,rear,columns,vertical=spec
    seed=index*1.17;angle=math.radians(degrees)
    n=Vector((math.cos(angle),math.sin(angle),0));along=Vector((-n.y,n.x,0));anchor=Vector((ax,ay,0))
    points=[];faces=[]
    base_center=anchor-n*24
    append_butte(points,faces,base_center,length*.69,82 if index<=37 else 75,min(bottom,-82),nominal-34,
                 angle+.12*math.sin(seed),0,0,seed,'base')
    count=2+(index%3)
    for group in range(count):
        fraction=(group+.5)/count-.5
        offset=fraction*.78*length
        summit=nominal-3-11*random_unit(group+1,seed)
        rx=length*(.27 if count==2 else .22 if count==3 else .17)
        ry=26+7*random_unit(group+3,seed)
        center=anchor+along*offset-n*(19+24*random_unit(group+8,seed))
        append_butte(points,faces,center,rx,ry,nominal-45,summit,
                     angle+.38*(random_unit(group+12,seed)-.5),0,0,seed+2.1+group*2.7,'upper')
    for group in range(2+(index%2)):
        offset=(group-.6)*length*.22
        center=base_center+n*(54+5*math.sin(seed+group))+along*offset
        append_butte(points,faces,center,14+6*random_unit(group+19,seed),13+4*random_unit(group+20,seed),
                     -39,nominal-50-8*random_unit(group+29,seed),angle+.35*math.sin(seed+group),0,0,seed+9.3+group,'spur')
    inverse=obj.matrix_world.inverted()
    mesh=bpy.data.meshes.new('Canyon_Far%02d_BrokenBeds_V19_04_L0'%index)
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
    scene.render.filepath=ROOT+'docs/p08/golden/canyon/v19/candidate04-gameplay.png'
    scene['v19_scope']='Unaccepted Far33-44 broken horizontal beds, staggered rock groups and interrupted talus; fixedV18-02camera/road/nearcliff. NoAssets export.'
    scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_03.blend'
    bpy.ops.wm.save_as_mainfile(filepath=DESTINATION,check_existing=False)
    print('CANYON_V19_BEDS04 '+json.dumps({'source':DESTINATION,'parentSource':SOURCE,'changedObjects':target_names,
        'layout':layout,'physicalSurfaces':surface_records,'audit':rows,'sceneLodTriangles':totals,'otherSceneMeshesExactlyUnchanged':len(outside),
        'cameraAndLightingExactlyUnchanged':True,'materialAndImageMembershipUnchanged':True,
        'fixedScene':fixed_before,'visualAccepted':False,'exportedToAssets':False}))
except Exception:
    bpy.ops.wm.open_mainfile(filepath=SOURCE)
    raise
