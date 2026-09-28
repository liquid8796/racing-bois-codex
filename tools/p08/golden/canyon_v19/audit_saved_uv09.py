import bpy,json,math
if not bpy.data.filepath.replace('\\','/').endswith('/Canyon/V19/RB_Golden_Canyon_V19_09.blend'):raise RuntimeError('Expected09.')
records=[{'object': 'Canyon_L0_Far_41', 'repairs': [{'vertices': [2539, 2767, 2768], 'beforeUv': [[0.09328532218933105, 0.2411138266324997], [0.09328532218933105, 0.2411138266324997], [0.09742549061775208, 0.20712026953697205]], 'afterUv': [[0.0716908723115921, 0.28969606757164], [0.08014260977506638, 0.19356244802474976], [0.08261380344629288, 0.19433291256427765]], 'physicalCrossSquared': 308.06515169143677, 'afterUvCross': 0.00024407655622937785, 'physicalProjectionExtentMetres': 18.142316177487373}, {'vertices': [2539, 2766, 2767], 'beforeUv': [[0.09328532218933105, 0.2411138266324997], [0.08428103476762772, 0.32202520966529846], [0.09328532218933105, 0.2411138266324997]], 'afterUv': [[0.0716908723115921, 0.28969606757164], [0.08013328909873962, 0.1936684548854828], [0.08502138406038284, 0.19464360177516937]], 'physicalCrossSquared': 1154.351230621338, 'afterUvCross': 0.0004776246862212563, 'physicalProjectionExtentMetres': 18.04412304237485}]}]
rows=[]
for record in records:
    obj=bpy.data.objects[record['object']];mesh=obj.data;mesh.calc_loop_triangles();layer=mesh.uv_layers[0]
    triangles={tuple(sorted(t.vertices)):t for t in mesh.loop_triangles}
    for repair in record['repairs']:
        triangle=triangles[tuple(sorted(repair['vertices']))]
        uv=[layer.data[i].uv for i in triangle.loops];actual=[[float(v.x),float(v.y)] for v in uv]
        cross=(float(uv[1].x)-uv[0].x)*(float(uv[2].y)-uv[0].y)-(float(uv[1].y)-uv[0].y)*(float(uv[2].x)-uv[0].x)
        points=[obj.matrix_world@mesh.vertices[i].co for i in triangle.vertices]
        physical=(points[1]-points[0]).cross(points[2]-points[0]).length_squared
        passed=actual==repair['afterUv'] and math.isfinite(cross) and abs(cross)>1e-14 and physical>1e-16
        rows.append({'object':obj.name,'vertices':list(triangle.vertices),'actualUv':actual,'uvCross':cross,'physicalCrossSquared':physical,'passed':passed})
print('CANYON_V19_SAVED_UV09 '+json.dumps({'rows':rows,'passed':all(r['passed'] for r in rows),'sourceSaved':False}))
if not all(r['passed'] for r in rows):raise RuntimeError('Saved physical projection check failed.')
