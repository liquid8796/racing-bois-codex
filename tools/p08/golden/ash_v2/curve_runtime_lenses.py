"""Replace flat runtime goggle panes with closed curved optical surfaces.

Only lens faces change. Existing face UVs, skin weights and expression geometry
are copied explicitly so removing obsolete lens vertices does not corrupt keys.
The tiny shared UV field is intentional: this glass finish is physically uniform.
"""
import bpy,math,json
from mathutils import Vector,Matrix
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
def lens_geometry(rows,cols):
    vertices=[];faces=[];uv=[]
    for side in [-1,1]:
        center=Vector((side*.048,-.156,1.786));horizontal=Vector((1,side*.45,0));vertical=Vector((0,.37,.929));normal=horizontal.cross(vertical).normalized()
        begin=len(vertices)
        for layer in range(2):
            for r in range(rows):
                v=-1+2*r/(rows-1);height=v*.0225;radius=.010
                limit=.039
                if abs(height)>.0225-radius:limit=.039-radius+math.sqrt(max(0,radius*radius-(abs(height)-(.0225-radius))**2))
                for c in range(cols):
                    u=-1+2*c/(cols-1);x=u*limit
                    bulge=.0042*(1-u*u)*(1-v*v)-layer*.0018
                    vertices.append(center+horizontal*x+vertical*height+normal*bulge)
                    uv.append((.6006+u*.010,.5186+v*.010))
        count=rows*cols
        for r in range(rows-1):
            for c in range(cols-1):
                i=begin+r*cols+c
                faces.append((i,i+1,i+1+cols,i+cols))
                i+=count;faces.append((i+cols,i+cols+1,i+1,i))
        edge=list(range(cols))+[r*cols+cols-1 for r in range(1,rows)]+list(range((rows-1)*cols+cols-2,(rows-1)*cols-1,-1))+[r*cols for r in range(rows-2,0,-1)]
        for i in range(len(edge)):
            a=begin+edge[i];b=begin+edge[(i+1)%len(edge)];faces.append((a,b,b+count,a+count))
    return vertices,faces,uv
report=[]
for level,rows,cols in [(0,13,19),(1,9,13),(2,5,9)]:
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin'];old=obj.data
    group_names=[group.name for group in obj.vertex_groups]
    material_index=next(i for i,mat in enumerate(old.materials) if mat.name=='AshV2_AmberLens_Baked')
    keep=[p for p in old.polygons if p.material_index!=material_index]
    used=sorted(set(i for p in keep for i in p.vertices));mapping={index:i for i,index in enumerate(used)}
    vertices=[old.vertices[i].co.copy() for i in used]
    original_weights=[[(g.group,g.weight) for g in old.vertices[i].groups] for i in used]
    expressions={key.name:[key.data[i].co.copy() for i in used] for key in old.shape_keys.key_blocks if key.name!='Basis'}
    faces=[tuple(mapping[i] for i in p.vertices) for p in keep];material_ids=[p.material_index for p in keep];smooth=[p.use_smooth for p in keep]
    uv_layers={layer.name:[[layer.data[i].uv.copy() for i in p.loop_indices] for p in keep] for layer in old.uv_layers}
    start=len(vertices);lens_vertices,lens_faces,lens_uv=lens_geometry(rows,cols);vertices.extend(lens_vertices)
    faces.extend(tuple(start+i for i in face) for face in lens_faces);material_ids.extend([material_index]*len(lens_faces));smooth.extend([True]*len(lens_faces))
    for name in uv_layers:uv_layers[name].extend([[lens_uv[i] for i in face] for face in lens_faces])
    materials=list(old.materials)
    obj.shape_key_clear()
    data=bpy.data.meshes.new(obj.name+'_CurvedOptics');data.from_pydata(vertices,[],faces);data.update();obj.data=data
    for name in group_names:obj.vertex_groups.new(name=name)
    for mat in materials:data.materials.append(mat)
    for polygon,index,shade in zip(data.polygons,material_ids,smooth):polygon.material_index=index;polygon.use_smooth=shade
    for name,face_uvs in uv_layers.items():
        layer=data.uv_layers.new(name=name)
        for polygon,values in zip(data.polygons,face_uvs):
            for loop,value in zip(polygon.loop_indices,values):layer.data[loop].uv=value
    data.uv_layers.active_index=0;data.uv_layers[0].active_render=True
    for index,values in enumerate(original_weights):
        for group,weight in values:obj.vertex_groups[group].add([index],weight,'REPLACE')
    head=obj.vertex_groups['RB_P06_Rider_L0_Head'];head.add(list(range(start,len(vertices))),1,'REPLACE')
    obj.shape_key_add(name='Basis',from_mix=False)
    for name,positions in expressions.items():
        key=obj.shape_key_add(name=name,from_mix=False);key.value=0
        for i,position in enumerate(positions):key.data[i].co=position
    data.calc_loop_triangles();report.append({'level':level,'triangles':len(data.loop_triangles),'vertices':len(data.vertices),'obsoleteLensVerticesRemoved':len(old.vertices)-len(used)})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend',compress=False)
print('ASH_CURVED_RUNTIME_OPTICS '+json.dumps(report))
