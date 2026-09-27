"""Observe intentional contacts in the authored engine assembly; counts are not visual-fidelity evidence."""
import bpy,json
from mathutils.bvhtree import BVHTree
def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@vertex.co for vertex in obj.data.vertices],
        [tuple(face.vertices) for face in obj.data.polygons],all_triangles=False,epsilon=0)
pairs=[('V2 conjoined lobed crankcase','V2 cylinder barrel 1'),
    ('V2 cylinder barrel 1','V2 rounded twin fin 00'),('V2 cylinder barrel 1','V2 domed rocker cover 1'),
    ('V2 conjoined lobed crankcase','V2 joined clutch cover 1'),
    ('V2 inlet runner 1','V2 round carburettor casting 1'),('V2 inlet runner 1','V2 cylinder head fin 03'),
    ('V2 conjoined lobed crankcase','V2 rear engine mounting lug 1'),
    ('V2 rear engine mounting lug 1','Seat triangle diagonal 1'),
    ('V2 countershaft bearing extension','V2 joined clutch cover 1')]
rows=[]
for first,second in pairs:rows.append({'first':first,'second':second,'surfaceIntersections':len(tree(bpy.data.objects[first]).overlap(tree(bpy.data.objects[second])))})
root=bpy.data.objects['RB_Golden_Spark_v2']
print('SPARK_V2_JOINTS='+json.dumps({'source':bpy.data.filepath,'meshComponents':sum(obj.type=='MESH' for obj in root.children_recursive),
    'intentionalContactObservations':rows,'visualAccepted':False,'scope':'Named joint surface observations only; zero can mean a gap or containment and requires separate interpretation.'}))
