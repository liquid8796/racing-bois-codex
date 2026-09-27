"""Repair the source cut hem and remove only derived runtime LOD copies.

Closed shell vertices are kept distinct during rebuild: welding touching shell
seams introduced nonmanifold edges into otherwise closed boot cuffs.
"""
import bpy,bmesh
from mathutils import Matrix
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/before-topology-repair.blend',copy=True)
clothes=bpy.data.objects['AshV2_Clothes'];bm=bmesh.new();bm.from_mesh(clothes.data)
cut_height=.236
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,cut_height),plane_no=(0,0,1),clear_inner=True)
for sign in [-1,1]:
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut_height)<1e-5 and v.co.x*sign>0 for v in e.verts)]
    if edges:bmesh.ops.bridge_loops(bm,edges=edges)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(clothes.data);bm.free()
for name in ['AshV2_L0_Skin','AshV2_L1_Skin','AshV2_L2_Skin','AshV2_HighResSource']:
    obj=bpy.data.objects.get(name)
    if obj:bpy.data.objects.remove(obj,do_unlink=True)
for name in ['Forward','Ground_L','Ground_R']:
    obj=bpy.data.objects.get(name)
    if obj:bpy.data.objects.remove(obj,do_unlink=True)
bpy.data.collections['AshV2_Editable_Source'].hide_viewport=False
bpy.context.view_layer.update()
print('ASH_HEM_REPAIRED_READY_FOR_DERIVED_LOD_REBUILD')
