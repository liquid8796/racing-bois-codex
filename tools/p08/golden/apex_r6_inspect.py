import bpy
import json
root=bpy.data.objects['RB_Golden_Apex_r5']
rows=[]
for obj in root.children_recursive:
    if obj.type=='MESH' and (obj.name.startswith('R4 formed main fairing') or obj.name.startswith('R3 Recessed black intake return') or obj.name.startswith('R5 cleared')):
        vs=[obj.matrix_world@v.co for v in obj.data.vertices]
        rows.append({'name':obj.name,'vertices':len(vs),'faces':len(obj.data.polygons),'smoothFaces':sum(p.use_smooth for p in obj.data.polygons),'min':[min(v[i] for v in vs) for i in range(3)],'max':[max(v[i] for v in vs) for i in range(3)],'materials':[m.name for m in obj.data.materials]})
print('R6_INSPECTION='+json.dumps({'file':bpy.data.filepath,'components':rows,'renderEngine':bpy.context.scene.render.engine,'resolution':[bpy.context.scene.render.resolution_x,bpy.context.scene.render.resolution_y]}))
