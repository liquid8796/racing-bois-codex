import bpy,json
result={}
for name in ['Canyon_L0_Road_00','Canyon_L0_Canyon_WhitePaint','Canyon_L0_Canyon_YellowPaint','Canyon_L0_Guardrail','Canyon_L0_Shoulder_-1','Canyon_L0_Shoulder_1','Canyon_L0_Sage']:
    obj=bpy.data.objects[name];normals=[p.normal for p in obj.data.polygons]
    result[name]={'positiveBlenderZ':sum(1 for n in normals if n.z>.1),'negativeBlenderZ':sum(1 for n in normals if n.z<-.1),'positiveX':sum(1 for n in normals if n.x>.1),'negativeX':sum(1 for n in normals if n.x<-.1),'firstNormals':[list(n) for n in normals[:4]]}
print('CANYON_NORMAL_PROBE '+json.dumps(result))
