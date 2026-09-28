"""Integrate the lamp openings into the side cowl and use a thin dark aperture gasket."""
import bpy
import bmesh
import math
import json
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/R6/RB_Golden_Apex_r6_editable20.blend')
root=bpy.data.objects['RB_Golden_Apex_r6']
assert bpy.data.objects.get('R6 thin lamp aperture gasket 1') is None

def finish(name,vertices,faces,material):
    mesh=bpy.data.meshes.new(name+' mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);obj.parent=root;obj['asset_group']='Body'
    mesh.materials.append(bpy.data.materials[material]);bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));nonmanifold=sum(not edge.is_manifold for edge in bm.edges);assert nonmanifold==0
    bm.to_mesh(mesh);bm.free();mesh.update();uv=mesh.uv_layers.new(name='UV0_SurfaceMetres')
    for face in mesh.polygons:
        face.use_smooth=True
        axis=0 if abs(face.normal.x)>=max(abs(face.normal.y),abs(face.normal.z)) else 1 if abs(face.normal.y)>=abs(face.normal.z) else 2
        axes=[i for i in range(3) if i!=axis]
        for loop in face.loop_indices:
            p=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(p[axes[0]]*2,p[axes[1]]*2)
    return {'name':name,'triangles':len(mesh.polygons),'nonManifoldEdges':nonmanifold}

rows=[]
for side in [-1,1]:
    source=bpy.data.objects['R4 swept continuous optical cowl '+str(side)]
    assert len(source.data.vertices)==672
    n=48;outer=[];inner=[]
    for j in range(n):
        a=source.matrix_world@source.data.vertices[5*n+j].co
        b=source.matrix_world@source.data.vertices[6*n+j].co
        outer.append(a.lerp(b,.66));inner.append(b)
    vertices=[]
    for offset in [.0015,.0003]:
        vertices.extend(p+Vector((0,offset,0)) for p in outer+inner)
    faces=[]
    for j in range(n):
        k=(j+1)%n
        faces += [(j,k,n+k,n+j),(2*n+j,3*n+j,3*n+k,2*n+k),
                  (j,2*n+j,2*n+k,k),(n+j,n+k,3*n+k,3*n+j)]
    rows.append(finish('R6 thin lamp aperture gasket '+str(side),vertices,faces,'Apex_Rubber'))

    # The former cowl ended at the lamp rim, leaving the optics visually hung
    # from the screen. A moulded cheek now returns into the side fairing.
    a=Vector((side*.232,.774,.808));b=Vector((side*.170,.806,.778))
    c=Vector((side*.290,.593,.665));d=Vector((side*.224,.765,.840))
    across=9;along=9;vertices=[];faces=[];count=across*along
    for layer in range(2):
        for i in range(along):
            t=i/(along-1)
            for j in range(across):
                u=j/(across-1)
                p=a*(1-u)*(1-t)+b*u*(1-t)+c*u*t+d*(1-u)*t
                p.x+=side*.010*math.sin(math.pi*u)*math.sin(math.pi*t)-side*layer*.004
                vertices.append(p)
    for layer in range(2):
        for i in range(along-1):
            for j in range(across-1):
                k=layer*count+i*across+j;face=(k,k+1,k+across+1,k+across)
                faces.append(face if layer==0 else tuple(reversed(face)))
    boundary=list(range(across))+[i*across+across-1 for i in range(1,along)]+[(along-1)*across+j for j in range(across-2,-1,-1)]+[i*across for i in range(along-2,0,-1)]
    for i,j in enumerate(boundary):
        k=boundary[(i+1)%len(boundary)];faces.append((j,k,k+count,j+count))
    rows.append(finish('R6 moulded lower optical cheek '+str(side),vertices,faces,'Apex_Pearl'))

chin=bpy.data.objects['R4 continuous lower nose return'];mesh=chin.data
assert len(mesh.vertices)==294
for vertex in mesh.vertices:
    index=vertex.index%147;row=index//49;col=index%49
    # Read a frozen top-row height for each column, retaining both solid layers.
    layer=vertex.index//147;top=mesh.vertices[layer*147+col].co.z
    vertex.co.z=top-row*.002
mesh.materials.clear();mesh.materials.append(bpy.data.materials['Apex_Rubber'])
for face in mesh.polygons:face.material_index=0
mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
root['r6Phase']='Cowl22: thin dark optical gasket, narrowed dark chin and moulded side-cheek continuity'
root['visualAccepted']=False
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable22.blend')
print('R6_COWL22='+json.dumps({'added':rows,'chinMaterial':'Apex_Rubber','chinReturnDepthMetres':.004,'saved':bpy.data.filepath,'visualAccepted':False}))
