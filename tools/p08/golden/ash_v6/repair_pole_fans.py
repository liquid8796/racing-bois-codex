import bpy,bmesh,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/';rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV6_L'+str(level)+'_HelmetShell'];bm=bmesh.new();bm.from_mesh(obj.data)
    deform=bm.verts.layers.deform.verify();group=obj.vertex_groups['RB_P06_Rider_L0_Head'].index
    caps=[f for f in bm.faces if len(f.verts)>4 and f.calc_center_median().z>1.84]
    assert len(caps)==2,'Expected exactly the two pole caps'
    for cap in caps:
        ring=list(cap.verts);z=1.854 if cap.calc_center_median().z>1.851 else 1.8492
        pole=bm.verts.new(Vector((0,-.041,z)));pole[deform][group]=1
        bmesh.ops.delete(bm,geom=[cap],context='FACES_ONLY')
        for i,a in enumerate(ring):bm.faces.new((pole,a,ring[(i+1)%len(ring)]))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
    rows.append({'lod':level,'ngonCapsReplaced':2,'realPoleVerticesAdded':2})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_POLE_FANS '+json.dumps(rows))
