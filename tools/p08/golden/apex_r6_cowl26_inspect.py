import bpy
import json
rows=[]
for side in [-1,1]:
    names=['R4 fitted windscreen side support '+str(side),'R4 integrated formed cowl shoulder '+str(side),'R4 swept continuous optical cowl '+str(side)]
    for name in names:
        obj=bpy.data.objects[name]
        indices=[0,5,6*6+5,9*6+5,12*6+5,18*6+5] if 'windscreen' in name else [0,12,8*13,8*13+12] if 'shoulder' in name else [16,18,20,22,24,26,28,30,32]
        rows.append({'name':name,'vertices':[{'i':i,'p':list(obj.matrix_world@obj.data.vertices[i].co)} for i in indices]})
print('COWL26_INPUTS='+json.dumps(rows))
