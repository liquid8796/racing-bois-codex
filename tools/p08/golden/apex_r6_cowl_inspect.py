import bpy
import json
root=bpy.data.objects['RB_Golden_Apex_r6']
rows=[]
for obj in root.children_recursive:
    if obj.type=='MESH' and any(word in obj.name.lower() for word in ['cowl','screen','nose','projector','lamp','optic']):
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        rows.append({'name':obj.name,'vertices':len(points),'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]})
print('COWL20_INPUTS='+json.dumps(rows))
