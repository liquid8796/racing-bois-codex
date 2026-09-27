"""Three independently staged Spark LODs. LOD1 retains exact tyre geometry."""
import bpy
import bmesh
import math
import json
from mathutils import Vector

scene=bpy.context.scene;NAME='RB_Golden_Spark_v1';root=bpy.data.objects[NAME]
assert not any(o.name.startswith('Spark_L0_') for o in root.children_recursive),'Reload editable source before assembly'
uv_factors={'Spark_Graphite':2,'Spark_Rubber':2,'Spark_Machined':8,'Spark_SatinSteel':4}

def marker(name,position):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=root;obj.location=position
for name,point in {'Forward':(0,1.1,0),'Semantic_Left':(-.5,0,0),'Semantic_Right':(.5,0,0),
    'Ground_Front':(0,.695,0),'Ground_Rear':(0,-.695,0),'Contact_Seat':(0,-.340,.800),
    'Contact_Grip_L':(-.330,.420,1.020),'Contact_Grip_R':(.330,.420,1.020),
    'Contact_Foot_L':(-.270,-.180,.335),'Contact_Foot_R':(.270,-.180,.335)}.items():marker(name,point)

def join_objects(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=bpy.context.object;obj.name=name
    return obj

groups={'Body':[],'Front':[],'Rear':[]};tyres={}
for obj in list(root.children_recursive):
    if obj.type!='MESH':continue
    group=obj.get('asset_group');assert group in groups,obj.name
    active=obj.data.uv_layers.active;assert active is not None,obj.name+' lacks UV'
    for layer in list(obj.data.uv_layers):
        if layer!=active:obj.data.uv_layers.remove(layer)
    active.name='UV0_SurfaceMetres';groups[group].append(obj)
    if 'road tyre with recessed channels' in obj.name:
        copy=obj.copy();copy.data=obj.data.copy();scene.collection.objects.link(copy);copy.name='Stage full tyre '+group;tyres[group]=copy
assert set(tyres)=={'Front','Rear'}

lod0={}
for group,objects in groups.items():
    obj=join_objects(objects,'Spark_L0_'+group)
    scene.cursor.location=(0,0,0) if group=='Body' else (0,.695 if group=='Front' else -.695,.315)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    matrix=obj.matrix_world.copy();obj.parent=root if group=='Body' else bpy.data.objects[NAME+'_Wheel_'+group];obj.matrix_world=matrix
    lod0[group]=obj

def remove_rubber(obj):
    indices={i for i,material in enumerate(obj.data.materials) if material.name=='Spark_Rubber'}
    bm=bmesh.new();bm.from_mesh(obj.data)
    remove=[face for face in bm.faces if face.material_index in indices]
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(obj.data);bm.free();obj.data.update()

def smooth_tyre(group):
    # LOD2 keeps the true rounded envelope. Detailed groove displacement is
    # below a pixel at the prescribed LOD2 distance; no ragged decimated tread.
    y=.695 if group=='Front' else -.695;width=.125 if group=='Front' else .160
    profile=[(-.5,.230),(-.51,.255),(-.46,.284),(-.34,.304),(-.17,.313),(0,.315),(.17,.313),(.34,.304),(.46,.284),(.51,.255),(.5,.230)]
    vertices=[];faces=[];segments=72;n=len(profile)
    for i in range(segments):
        a=math.tau*i/segments
        for j,(x,radius) in enumerate(profile):
            vertices.append((x*width,y+radius*math.sin(a),.315+radius*math.cos(a)))
            ni,nj=(i+1)%segments,(j+1)%n;faces.append((i*n+j,ni*n+j,ni*n+nj,i*n+nj))
    data=bpy.data.meshes.new('Spark LOD2 '+group+' tyre');data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new('Stage smooth tyre '+group,data);scene.collection.objects.link(obj);obj.parent=root
    data.materials.append(bpy.data.materials['Spark_Rubber']);uv=data.uv_layers.new(name='UV0_SurfaceMetres')
    for face in data.polygons:
        face.use_smooth=True
        for loop in face.loop_indices:
            vertex=data.loops[loop].vertex_index;i,j=divmod(vertex,n)
            u=i/segments
            if i==0 and any(data.loops[k].vertex_index//n==segments-1 for k in face.loop_indices):u=1
            uv.data[loop].uv=(u*8,j/n*2)
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    return obj

for group,original in lod0.items():
    for level,ratio in [(1,.50),(2,.22)]:
        obj=original.copy();obj.data=original.data.copy();scene.collection.objects.link(obj);obj.name='Spark_L%d_'%level+group
        if group!='Body':remove_rubber(obj)
        bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('Reduced mechanisms; tyre envelope separate','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
        if group!='Body':
            tyre=tyres[group] if level==1 else smooth_tyre(group)
            obj=join_objects([obj,tyre],'Spark_L%d_'%level+group)
        obj.hide_render=True

def discard_collapsed_micro_parts(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);seen=set();remove=set();face_count=0
    for seed in bm.verts:
        if seed in seen:continue
        component=set();todo=[seed]
        while todo:
            v=todo.pop()
            if v in component:continue
            component.add(v);seen.add(v)
            for edge in v.link_edges:todo.append(edge.other_vert(v))
        edges={e for v in component for e in v.link_edges};faces={f for v in component for f in v.link_faces}
        if not faces:remove.update(component);continue
        if not any(not edge.is_manifold for edge in edges):continue
        first=next(iter(component));end=first
        for v in component:
            if (v.co-first.co).length_squared>(end.co-first.co).length_squared:end=v
        start=end
        for v in component:
            if (v.co-end.co).length_squared>(start.co-end.co).length_squared:start=v
        axis=(end.co-start.co).normalized();radius=max((v.co-start.co).cross(axis).length for v in component)
        assert len(faces)<=6 and radius<.006 and sum(f.calc_area() for f in faces)<.001,'Nontrivial LOD part broke: '+obj.name
        remove.update(component);face_count+=len(faces)
    assert face_count<len(bm.faces)*.10,'Excessive LOD micro-part removal'
    if remove:bmesh.ops.delete(bm,geom=list(remove),context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
    return len(remove)

rows=[];failures=0
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    bpy.context.view_layer.objects.active=obj;mod=obj.modifiers.new('Explicit export triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    removed=discard_collapsed_micro_parts(obj) if '_L0_' not in obj.name else 0
    obj.data.calc_loop_triangles();bad=0;uv=obj.data.uv_layers.active;repaired=0
    for face in obj.data.polygons:
        p=[uv.data[i].uv for i in face.loop_indices]
        area=abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))*.5
        if area<1e-12:
            axis=0 if abs(face.normal.x)>=max(abs(face.normal.y),abs(face.normal.z)) else 1 if abs(face.normal.y)>=abs(face.normal.z) else 2
            axes=[i for i in range(3) if i!=axis];factor=2*uv_factors.get(obj.data.materials[face.material_index].name,1)
            origin=obj.data.vertices[obj.data.loops[face.loop_start].vertex_index].co
            for loop in face.loop_indices:
                p=obj.data.vertices[obj.data.loops[loop].vertex_index].co-origin;uv.data[loop].uv=(p[axes[0]]*factor,p[axes[1]]*factor)
            repaired+=1
    for tri in obj.data.loop_triangles:
        a,b,c=[obj.matrix_world@obj.data.vertices[i].co for i in tri.vertices];bad+=(b-a).cross(c-a).length_squared<=1e-16
    bm=bmesh.new();bm.from_mesh(obj.data);topology=sum(not e.is_manifold for e in bm.edges);bm.free()
    failures+=bad+topology;rows.append({'name':obj.name,'triangles':len(obj.data.loop_triangles),'physicalFailures':bad,'nonManifoldEdges':topology,'uvCapRepairs':repaired,'removedCollapsedLodVertices':removed})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_assembled.blend')
print('SPARK_ASSEMBLED='+json.dumps({'objects':rows,'structuralFailures':failures,'lod1TyresRetainedExactly':True,'lod2TyresAuthoredRoundedEnvelope':True,'visualAccepted':False}))
assert failures==0,'Do not export broken source'
