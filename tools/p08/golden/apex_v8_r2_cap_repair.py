"""Fan the two tank-mount caps, eliminating a collinear ear-clipping sliver."""
import bpy,bmesh
obj=bpy.data.objects['Tank underside knee mounting']
bm=bmesh.new();bm.from_mesh(obj.data)
caps=[f for f in bm.faces if len(f.verts)>4]
bmesh.ops.poke(bm,faces=caps,offset=0.0,center_mode='MEAN',use_relative_offset=False)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(obj.data);bm.free();obj.data.update()
print('R2 tank-mount cap topology replaced with centered fans; outer silhouette unchanged.')
