"""Fresh study25: match nose/collar to actual optical boundaries; rake the existing screen rearward."""
import bpy
import bmesh
import json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/R6/RB_Golden_Apex_r6_editable24.blend')
root=bpy.data.objects['RB_Golden_Apex_r6']
assert not root.get('r6_cowl25')

def update(obj):
    obj.data.update();bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(edge.is_manifold for edge in bm.edges),obj.name
    bm.to_mesh(obj.data);bm.free();obj.data.update();obj.data.normals_split_custom_set([(0,0,0)]*len(obj.data.loops))

def panel(name,grid,material):
    nr=len(grid);nc=len(grid[0]);verts=[p.copy() for row in grid for p in row];count=len(verts)
    verts.extend(p-Vector((0,.004,0)) for p in verts[:count]);faces=[]
    for r in range(nr-1):
        for c in range(nc-1):
            a=r*nc+c;b=a+1;d=a+nc;e=d+1
            faces.extend([(a,b,e,d),(d+count,e+count,b+count,a+count)])
    boundary=list(range(nc))+[r*nc+nc-1 for r in range(1,nr)]+[(nr-1)*nc+c for c in range(nc-2,-1,-1)]+[r*nc for r in range(nr-2,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.append((a,a+count,b+count,b))
    mesh=bpy.data.meshes.new(name+' mesh');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);obj.parent=root;obj['asset_group']='Body';mesh.materials.append(bpy.data.materials[material]);update(obj)
    uv=mesh.uv_layers.new(name='UV0_SurfaceMetres')
    for f in mesh.polygons:
        f.use_smooth=True;axis=0 if abs(f.normal.x)>=max(abs(f.normal.y),abs(f.normal.z)) else 1 if abs(f.normal.y)>=abs(f.normal.z) else 2;axes=[i for i in range(3) if i!=axis]
        for li in f.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]*2,p[axes[1]]*2)
    return obj

changed=[]
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    n=obj.name;kind=''
    if n=='R4 attached double-curved windscreen':kind='screen'
    elif n=='R4 screen lower seated seal':kind='base'
    elif n.startswith('R4 screen thin side rim'):kind='rim'
    elif n.startswith('R4 fitted windscreen side support'):kind='support'
    if not kind:continue
    world=obj.matrix_world;inverse=world.inverted()
    for vertex in obj.data.vertices:
        i=vertex.index
        if kind=='screen':t=((i%551)//29)/18
        elif kind=='base':t=0
        elif kind=='rim':t=(i//8)/18 if i<152 else 0 if i==152 else 1
        else:t=((i%114)//6)/18
        p=world@vertex.co;p.y-=.055+.075*t;vertex.co=inverse@p
    update(obj);changed.append(n)

edges={}
for side in [-1,1]:
    obj=bpy.data.objects['R4 swept continuous optical cowl '+str(side)]
    assert len(obj.data.vertices)==672
    edges[side]=[obj.matrix_world@obj.data.vertices[i].co for i in range(2,19)]
    assert all(b.z>a.z for a,b in zip(edges[side],edges[side][1:])), 'Inner optical edge must rise continuously'

grid=[]
for left,right in zip(edges[-1],edges[1]):
    row=[]
    for col in range(29):
        q=col/14-1;p=left.lerp(right,col/28);p.y+=.006*(1-q*q);row.append(p)
    grid.append(row)
old=bpy.data.objects['R4 fitted central nose blade'];bpy.data.objects.remove(old,do_unlink=True)
nose=panel('R6 optical-boundary central nose blade',grid,'Apex_Graphite')
glass=bpy.data.objects['R4 attached double-curved windscreen'];base=[glass.matrix_world@glass.data.vertices[i].co for i in range(29)]
collar=[]
for r in range(7):
    t=r/6;collar.append([a.lerp(b,t) for a,b in zip(grid[-1],base)])
old=bpy.data.objects['R4 fitted screen collar'];bpy.data.objects.remove(old,do_unlink=True)
panel('R6 matched dark screen-to-nose collar',collar,'Apex_Graphite')
root['r6_cowl25']=True;root['r6Phase']='Cowl25: actual optical-edge centre closure and matched dark screen collar, raked screen';root['visualAccepted']=False
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable25.blend')
print('R6_COWL25='+json.dumps({'saved':bpy.data.filepath,'screenParts':changed,'screenBaseRearwardMetres':.055,'screenCrownRearwardMetres':.130,'noseEdges':{'left':[list(p) for p in edges[-1]],'right':[list(p) for p in edges[1]]},'visualAccepted':False,'mirrorMountsUnchanged':True}))
