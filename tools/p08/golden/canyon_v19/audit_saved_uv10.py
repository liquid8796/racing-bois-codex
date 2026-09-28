import bpy,json,math
if not bpy.data.filepath.replace('\\','/').endswith('/Canyon/V19/RB_Golden_Canyon_V19_10.blend'):raise RuntimeError('Expected10.')
records=[]
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
print('CANYON_V19_SAVED_UV10 '+json.dumps({'rows':rows,'passed':all(r['passed'] for r in rows),'sourceSaved':False}))
if not all(r['passed'] for r in rows):raise RuntimeError('Saved physical projection check failed.')
