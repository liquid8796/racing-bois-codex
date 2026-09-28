"""Join the screen side to the existing upper cowl boundary and reattach mirror bases to it."""
import bpy
import bmesh
import math
import json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/R6/RB_Golden_Apex_r6_editable25.blend')
root=bpy.data.objects['RB_Golden_Apex_r6'];glass=bpy.data.objects['R4 attached double-curved windscreen'];rows=[]

def update(obj):
    obj.data.update();bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),obj.name
    bm.to_mesh(obj.data);bm.free();obj.data.update();obj.data.normals_split_custom_set([(0,0,0)]*len(obj.data.loops))

def bridge(name,grid,side):
    nr=len(grid);nc=len(grid[0]);verts=[p.copy() for row in grid for p in row];n=len(verts);verts.extend(p-Vector((side*.004,0,0)) for p in verts[:n]);faces=[]
    for r in range(nr-1):
        for c in range(nc-1):
            a=r*nc+c;b=a+1;d=a+nc;e=d+1;faces.extend([(a,b,e,d),(d+n,e+n,b+n,a+n)])
    ring=list(range(nc))+[r*nc+nc-1 for r in range(1,nr)]+[(nr-1)*nc+c for c in range(nc-2,-1,-1)]+[r*nc for r in range(nr-2,0,-1)]
    for a,b in zip(ring,ring[1:]+ring[:1]):faces.append((a,a+n,b+n,b))
    mesh=bpy.data.meshes.new(name+' mesh');mesh.from_pydata(verts,[],faces);mesh.update();obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);obj.parent=root;obj['asset_group']='Body';mesh.materials.append(bpy.data.materials['Apex_Pearl']);update(obj)
    uv=mesh.uv_layers.new(name='UV0_SurfaceMetres')
    for f in mesh.polygons:
        f.use_smooth=True;axis=0 if abs(f.normal.x)>=max(abs(f.normal.y),abs(f.normal.z)) else 1 if abs(f.normal.y)>=abs(f.normal.z) else 2;axes=[i for i in range(3) if i!=axis]
        for li in f.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]*2,p[axes[1]]*2)
    return obj

for side in [-1,1]:
    support=bpy.data.objects['R4 fitted windscreen side support '+str(side)];optical=bpy.data.objects['R4 swept continuous optical cowl '+str(side)];shoulder=bpy.data.objects['R4 integrated formed cowl shoulder '+str(side)]
    peak=optical.matrix_world@optical.data.vertices[18].co;edge_col=0 if side<0 else 28;bottom=glass.matrix_world@glass.data.vertices[edge_col].co;initial=peak-bottom;outer=[]
    for r in range(19):
        t=r/18;a=glass.matrix_world@glass.data.vertices[r*29+edge_col].co;blend=min(1,t/.3333333333);blend=blend*blend*(3-2*blend)
        offset=initial.lerp(Vector((side*.032,.003,-.015)),blend);outer.append(a+offset)
        for c in range(6):
            p=a.lerp(outer[-1],c/5)
            for layer in range(2):support.data.vertices[layer*114+r*6+c].co=support.matrix_world.inverted()@(p-Vector((side*.004*layer,0,0)))
    update(support)
    grid=[]
    for r in range(13):
        t=r/12;si=t*8;lo=int(si);hi=min(8,lo+1);a=shoulder.matrix_world@shoulder.data.vertices[lo*13].co;b=shoulder.matrix_world@shoulder.data.vertices[hi*13].co;lower=a.lerp(b,si-lo)
        if r==0:lower=optical.matrix_world@optical.data.vertices[26].co
        row=[]
        for c in range(9):
            u=c/8;p=outer[r].lerp(lower,u);p.x+=side*.003*math.sin(math.pi*u)*math.sin(math.pi*t);row.append(p)
        grid.append(row)
    bridge('R6 continuous upper optical shoulder '+str(side),grid,side)
    boot=bpy.data.objects['R4 fairing mirror mount boot '+str(side)];arm=bpy.data.objects['R4 broad connected mirror arm '+str(side)]
    assert len(boot.data.vertices)==34 and len(arm.data.vertices)==50
    old_boot=boot.matrix_world@boot.data.vertices[32].co;old_arm=arm.matrix_world@arm.data.vertices[48].co;anchor=outer[9]+Vector((side*.003,0,.002));delta=anchor-old_boot
    for vertex in boot.data.vertices:vertex.co=boot.matrix_world.inverted()@(boot.matrix_world@vertex.co+delta)
    update(boot)
    arm_delta=anchor+Vector((0,0,.002))-old_arm
    for vertex in arm.data.vertices:
        p=arm.matrix_world@vertex.co;w=max(0,min(1,(p.y-.490)/(old_arm.y-.490)));p+=arm_delta*w;vertex.co=arm.matrix_world.inverted()@p
    update(arm)
    rows.append({'side':side,'mirrorBaseBefore':list(old_boot),'mirrorBaseAfter':list(anchor),'upperShoulderFront':[list(p) for p in grid[0]],'unchangedMirrorCases':True})
root['r6Phase']='Cowl26: upper optical shell joined to screen support and mirror feet reattached';root['visualAccepted']=False
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable26.blend')
print('R6_COWL26='+json.dumps({'saved':bpy.data.filepath,'sides':rows,'visualAccepted':False}))
