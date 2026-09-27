import bpy,json
obj=bpy.data.objects['V2 copper teardrop tank'];data=obj.data;data.calc_loop_triangles();rows=[]
for triangle in data.loop_triangles:
    points=[data.vertices[index].co for index in triangle.vertices];a,b,c=points
    cross=(b-a).cross(c-a).length_squared
    if cross<=1e-16:
        rows.append({'polygon':triangle.polygon_index,'vertices':list(triangle.vertices),'points':[list(p) for p in points],
            'edgeLengths':[(b-a).length,(c-b).length,(a-c).length],'crossSquared':cross})
print('SPARK_TANK_DEGENERATES='+json.dumps(rows))
