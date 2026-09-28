"""Fresh checkpoint after fairing05: original seat/tank side infills from the locked concept."""
import bpy
import bmesh
import json
from mathutils import Vector

ROOT = 'D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\', '/').endswith('/R6/RB_Golden_Apex_r6_editable05.blend')
root = bpy.data.objects['RB_Golden_Apex_r6']
assert bpy.data.objects.get('R6 pearl seat-to-tank bridge 1') is None

def closed_panel(name, outer, material, thickness):
    side = 1 if outer[0][0] > 0 else -1
    vertices = [Vector(p) for p in outer] + [Vector((p[0]-side*thickness,p[1],p[2])) for p in outer]
    count = len(outer)
    faces = [tuple(range(count)), tuple(reversed(range(count,count*2)))]
    faces += [(j,(j+1)%count,(j+1)%count+count,j+count) for j in range(count)]
    mesh = bpy.data.meshes.new(name+' mesh'); mesh.from_pydata(vertices,[],faces);mesh.update()
    obj = bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);obj.parent=root;obj['asset_group']='Body'
    mesh.materials.append(bpy.data.materials[material])
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bmesh.ops.bevel(bm,geom=list(bm.edges),offset=.0012,segments=2,affect='EDGES',clamp_overlap=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    nonmanifold=sum(not edge.is_manifold for edge in bm.edges);assert nonmanifold==0
    bm.to_mesh(mesh);bm.free();mesh.update()
    uv=mesh.uv_layers.new(name='UV0_SurfaceMetres')
    for face in mesh.polygons:
        face.use_smooth=False
        axis=0 if abs(face.normal.x)>=max(abs(face.normal.y),abs(face.normal.z)) else 1 if abs(face.normal.y)>=abs(face.normal.z) else 2
        axes=[i for i in range(3) if i!=axis]
        for loop in face.loop_indices:
            p=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(p[axes[0]]*2,p[axes[1]]*2)
    return {'name':name,'vertices':len(mesh.vertices),'triangles':len(mesh.polygons),'nonManifoldEdges':nonmanifold}

rows=[]
for side in [-1,1]:
    white=[(.153,-.477,.802),(.124,-.217,.818),(.158,-.100,.785),(.213,-.032,.765),(.207,-.163,.714),(.149,-.339,.746),(.149,-.476,.765)]
    rows.append(closed_panel('R6 pearl seat-to-tank bridge '+str(side),[(side*x,y,z) for x,y,z in white],'Apex_Pearl',.006))
    black=[(.116,-.200,.781),(.135,-.070,.786),(.144,.110,.810),(.170,.290,.848),(.170,.285,.817),(.162,.037,.742),(.150,-.158,.709),(.121,-.212,.750)]
    rows.append(closed_panel('R6 recessed tank sill insert '+str(side),[(side*x,y,z) for x,y,z in black],'Apex_Graphite',.004))
root['r6Phase']='Seat/tank infill study10; fairing05 retained'
root['visualAccepted']=False
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable10.blend')
print('R6_INFILL10='+json.dumps({'added':rows,'saved':bpy.data.filepath,'visualAccepted':False,'fixed':'Tank, saddle, frame, wheelbase and contact anchors not transformed'}))
