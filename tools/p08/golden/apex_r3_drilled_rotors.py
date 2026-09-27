"""Replace inherited rotor hole markers with actual through-drilled geometry."""
import bpy,bmesh,math,json
from mathutils import Vector
root=bpy.data.objects['RB_Golden_Apex_r3'];scene=bpy.context.scene;rows=[]
for o in list(root.children_recursive):
    if o.name.startswith('Recessed rotor drilling'):bpy.data.objects.remove(o,do_unlink=True)
for obj in [o for o in root.children_recursive if 'brake swept ring' in o.name]:
    group=obj.get('asset_group');front=group=='Front';z=.715 if front else -.715
    x=sum((obj.matrix_world@v.co).x for v in obj.data.vertices)/len(obj.data.vertices)
    radius=.150 if front else .114;verts=[];faces=[];sides=12
    for j in range(48):
        a=j*math.tau/48;r=radius-.010-(j%2)*.014;yy=.315+r*math.cos(a);zz=z+r*math.sin(a);base=len(verts)
        for xx in [x-.014,x+.014]:
            for k in range(sides):
                angle=k*math.tau/sides;verts.append((xx,zz+.0026*math.sin(angle),yy+.0026*math.cos(angle)))
        for k in range(sides):faces.append((base+k,base+(k+1)%sides,base+sides+(k+1)%sides,base+sides+k))
        faces.append(tuple(base+k for k in range(sides-1,-1,-1)));faces.append(tuple(base+sides+k for k in range(sides)))
    data=bpy.data.meshes.new('R3 Drilling Tool');data.from_pydata(verts,[],faces);data.update()
    cutter=bpy.data.objects.new('R3 Temporary Rotor Drilling Tool',data);scene.collection.objects.link(cutter)
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    bpy.context.view_layer.objects.active=obj;modifier=obj.modifiers.new('Real drilled cooling holes','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name);bpy.data.objects.remove(cutter,do_unlink=True)
    obj.data.materials.clear();obj.data.materials.append(bpy.data.materials['Apex_Machined'])
    for face in obj.data.polygons:face.material_index=0
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.dissolve_degenerate(bm,dist=.000015,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.validate(clean_customdata=False);obj.data.update()
    # Matching projected charts retain a physical repeating brushed finish.
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UV_RotorMachining')
    for face in obj.data.polygons:
        axis=0 if abs(face.normal.x)>=max(abs(face.normal.y),abs(face.normal.z)) else 1 if abs(face.normal.y)>=abs(face.normal.z) else 2;axes=[i for i in range(3) if i!=axis]
        for loop in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[loop].vertex_index].co;uv.data[loop].uv=(p[axes[0]]*3,p[axes[1]]*3)
    obj.data.calc_loop_triangles();rows.append({'name':obj.name,'actualThroughHoles':48,'triangles':len(obj.data.loop_triangles)})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend')
print('APEX_R3_DRILLED_ROTORS '+json.dumps({'rotors':rows,'visualAccepted':False}))
