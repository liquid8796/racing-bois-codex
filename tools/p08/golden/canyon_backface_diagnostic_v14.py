import bpy,bmesh,json
from mathutils import Vector
root=bpy.data.objects['RB_Golden_Canyon'];camera=bpy.context.scene.camera.location
rows=[]
for obj in root.children_recursive:
    if obj.type!='MESH' or '_L0_' not in obj.name:continue
    if not any(m.name in ['Canyon_Cliff01','Canyon_Cliff02','Canyon_Cliff03'] for m in obj.data.materials):continue
    bm=bmesh.new();bm.from_mesh(obj.data)
    boundary=sum(1 for edge in bm.edges if edge.is_boundary);nonmanifold=sum(1 for edge in bm.edges if not edge.is_manifold)
    volume=bm.calc_volume(signed=True)
    total=0.0;front=0.0;normal_sum=Vector((0,0,0));matrix=obj.matrix_world;normal_matrix=matrix.to_3x3().inverted().transposed()
    for face in obj.data.polygons:
        normal=(normal_matrix@face.normal).normalized();area=face.area;total+=area;normal_sum+=normal*area
        if normal.dot(camera-matrix@face.center)>0:front+=area
    rows.append({'name':obj.name,'material':obj.data.materials[0].name,'matrixDeterminant':matrix.determinant(),'boundaryEdges':boundary,'nonManifoldEdges':nonmanifold,'signedLocalVolume':volume,'areaFacingCameraFraction':front/total,'areaWeightedWorldNormal':list(normal_sum/total)})
    bm.free()
print('CANYON_BACKFACE_DIAGNOSTIC '+json.dumps(rows))
