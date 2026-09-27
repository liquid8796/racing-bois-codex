"""V2 revision 03: coherent outboard drive plane and proper extended tank clearance tools."""
import bpy,bmesh,json,math
from mathutils import Vector
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
assert bpy.data.filepath.replace('\\','/').endswith('/Spark/V2/RB_Golden_Spark_v2_editable.blend')
scene=bpy.context.scene;scene.blendermcp_auto_start_server=False;root=bpy.data.objects['RB_Golden_Spark_v2']
changed=[]
drive_prefixes=['Drive chain','Rear drive sprocket','Countershaft drive sprocket']
exhaust_prefixes=['Swept connected header','Satin stacked silencer','Dark silencer outlet','Deep silencer throat',
    'Silencer joining band','Collector perforated heat shield','Silencer perforated front guard','Heat-shield retaining screw']
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    if any(obj.name.startswith(prefix) for prefix in drive_prefixes):
        for vertex in obj.data.vertices:vertex.co.x+=.170
        changed.append({'object':obj.name,'change':'drive plane +0.170m to x+0.245m'})
    elif any(obj.name.startswith(prefix) for prefix in exhaust_prefixes):
        for vertex in obj.data.vertices:
            t=max(0,min(1,(.239-vertex.co.y)/.339));vertex.co.x+=.075*t*t*(3-2*t)
        changed.append({'object':obj.name,'change':'downstream exhaust +0.075m; original front ports held'})
    elif obj.name.startswith('Silencer connected hanger'):
        for vertex in obj.data.vertices:
            t=max(0,min(1,(vertex.co.x-.146)/.085));vertex.co.x+=.075*t
        changed.append({'object':obj.name,'change':'outer silencer attachment +0.075m; inner frame attachment held'})
    obj.data.update()

def cylinder(name,a,b,radius,material,parent=root,group='Body'):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized();helper=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((1,0,0))
    u=axis.cross(helper).normalized();v=axis.cross(u).normalized();vertices=[];faces=[];n=40
    for center in [a,b]:
        for j in range(n):
            angle=math.tau*j/n;vertices.append(center+radius*(u*math.cos(angle)+v*math.sin(angle)))
    vertices.extend([a,b])
    for j in range(n):faces.extend([(j,(j+1)%n,n+(j+1)%n,n+j),(2*n,(j+1)%n,j),(2*n+1,n+j,n+(j+1)%n)])
    data=bpy.data.meshes.new(name+' mesh');data.from_pydata(vertices,[],faces);data.update()
    value=bpy.data.objects.new(name,data);scene.collection.objects.link(value);value.parent=parent;value['asset_group']=group
    data.materials.append(bpy.data.materials[material]);uv=data.uv_layers.new(name='UV0_SurfaceMetres')
    for face in data.polygons:
        face.use_smooth=len(face.vertices)==4
        normal=face.normal;omit=0 if abs(normal.x)>=max(abs(normal.y),abs(normal.z)) else 1 if abs(normal.y)>=abs(normal.z) else 2
        axes=[i for i in range(3) if i!=omit]
        for loop in face.loop_indices:
            p=data.vertices[data.loops[loop].vertex_index].co;uv.data[loop].uv=(p[axes[0]]*2,p[axes[1]]*2)
    return value

bpy.data.objects.remove(bpy.data.objects['Countershaft connector'],do_unlink=True)
cylinder('V2 countershaft bearing extension',(.188,-.195,.405),(.245,-.195,.405),.016,'SparkV2_CastBlack')
cylinder('V2 rear drive hub spacer',(.061,-.695,.315),(.246,-.695,.315),.020,'SparkV2_CastBlack',group='Rear')

def difference(target,cutter):
    try:
        target.select_set(True)
        bpy.context.view_layer.objects.active=target
        modifier=target.modifiers.new('Measured mechanical clearance','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    finally:bpy.data.objects.remove(cutter,do_unlink=True)

def expanded_tube(name,sides):
    source=bpy.data.objects[name];value=source.copy();value.data=source.data.copy();scene.collection.objects.link(value)
    value.name='V2 owned extended tube tool '+name
    count=len(value.data.vertices);assert (count-2)%sides==0
    ring_count=(count-2)//sides
    centers=[]
    for first in range(0,count-2,sides):centers.append(sum((value.data.vertices[first+j].co for j in range(sides)),Vector())/sides)
    for ring,center in enumerate(centers):
        extension=Vector()
        if ring==0:extension=(centers[0]-centers[1]).normalized()*.040
        if ring==ring_count-1:extension=(centers[-1]-centers[-2]).normalized()*.040
        for j in range(sides):
            vertex=value.data.vertices[ring*sides+j];vertex.co=center+(vertex.co-center)*1.45+extension
    value.data.vertices[count-2].co+=(centers[0]-centers[1]).normalized()*.040
    value.data.vertices[count-1].co+=(centers[-1]-centers[-2]).normalized()*.040
    value.data.update();return value

tank=bpy.data.objects['V2 copper teardrop tank']
for name,sides in [('Steering head',28),('Upper black frame rail -1',14),('Upper black frame rail 1',14)]:
    difference(tank,expanded_tube(name,sides))
source=bpy.data.objects['Upper triple clamp'];cutter=source.copy();cutter.data=source.data.copy();scene.collection.objects.link(cutter)
for vertex in cutter.data.vertices:vertex.co+=vertex.normal*.008
cutter.data.update();difference(tank,cutter)

mesh=tank.data;bm=bmesh.new();bm.from_mesh(mesh)
before_vertices=len(bm.verts)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()

repaired=[]
for obj in [tank,bpy.data.objects['V2 wrapped passenger strap'],bpy.data.objects['V2 countershaft bearing extension'],bpy.data.objects['V2 rear drive hub spacer']]:
    data=obj.data;data.calc_loop_triangles();uv=data.uv_layers.active
    if uv is None:uv=data.uv_layers.new(name='UV0_SurfaceMetres')
    bad=set()
    for tri in data.loop_triangles:
        a,b,c=[uv.data[i].uv for i in tri.loops]
        if abs((b.x-a.x)*(c.y-a.y)-(c.x-a.x)*(b.y-a.y))<=2e-12:bad.add(tri.polygon_index)
    for i in bad:
        face=data.polygons[i];normal=face.normal
        axis=0 if abs(normal.x)>=max(abs(normal.y),abs(normal.z)) else 1 if abs(normal.y)>=abs(normal.z) else 2
        axes=[j for j in range(3) if j!=axis];origin=data.vertices[data.loops[face.loop_start].vertex_index].co
        for loop in face.loop_indices:
            point=data.vertices[data.loops[loop].vertex_index].co-origin
            uv.data[loop].uv=(.02+point[axes[0]]*.08,.50+point[axes[1]]*.08) if obj==tank else (point[axes[0]]*2,point[axes[1]]*2)
    repaired.append({'object':obj.name,'faces':len(bad)})

root['drivePlaneMetres']=.245;root['clearanceRevision']=3
root['visualAccepted']=False
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_refined03.blend',compress=True)
print('SPARK_V2_MECHANICAL_CLEARANCE='+json.dumps({'source':bpy.data.filepath,'changedMeshes':changed,'drivePlaneMetres':.245,'silencerOutboardShiftMetres':.075,
    'tankVerticesRemoved':before_vertices-len(mesh.vertices),'uvRepairs':repaired,'canonicalAnchorsChanged':False,'visualAccepted':False,'exported':False}))
