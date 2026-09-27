import bpy,json
obj=bpy.data.objects['AshV2_OpenFaceHelmetShell'];layer=obj.data.uv_layers.active
points=[x.uv for x in layer.data]
print(json.dumps({'sourceHelmetLayers':[uv.name for uv in obj.data.uv_layers],'bounds':[min(p.x for p in points),min(p.y for p in points),max(p.x for p in points),max(p.y for p in points)],'sample':[list(p) for p in points[:16]]}))
