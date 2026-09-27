import bpy,bmesh,json
o=bpy.data.objects['AshV6_L2_Equipment'];bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table()
faces=[bm.faces[i] for i in [1130,1134]]
assert all(len(f.verts)==4 for f in faces)
bmesh.ops.triangulate(bm,faces=faces,quad_method='ALTERNATE');bm.to_mesh(o.data);bm.free();o.data.update()
print('ASH_V6_SOCKET_TRIANGULATION '+json.dumps({'lod':2,'quads':2,'verticesMoved':0,'uvCoordinatesMoved':0,'reason':'three collinear vertices on shell-projected gasket edge; alternate diagonal has finite physical area'}))
