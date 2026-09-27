"""Read-only mesh, contact and named mechanical clearance checks; no visual acceptance."""
import bpy,bmesh,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=bpy.data.objects['RB_Golden_Spark_v2']
bpy.context.view_layer.update()
def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@vertex.co for vertex in obj.data.vertices],
        [tuple(face.vertices) for face in obj.data.polygons],all_triangles=False,epsilon=0)
rows=[];new_objects=[obj for obj in root.children_recursive if obj.type=='MESH' and obj.name.startswith('V2 ')]
for obj in new_objects:
    data=obj.data;data.calc_loop_triangles();bad=0;uv_bad=0
    for tri in data.loop_triangles:
        a,b,c=[obj.matrix_world@data.vertices[index].co for index in tri.vertices]
        bad+=(b-a).cross(c-a).length_squared<=1e-16
        u,v,w=[data.uv_layers.active.data[index].uv for index in tri.loops]
        uv_bad+=abs((v.x-u.x)*(w.y-u.y)-(w.x-u.x)*(v.y-u.y))<=2e-12
    bm=bmesh.new();bm.from_mesh(data);nonmanifold=sum(not edge.is_manifold for edge in bm.edges);bm.free()
    if bad or uv_bad or nonmanifold:rows.append({'name':obj.name,'badPhysicalTriangles':bad,'badUvTriangles':uv_bad,'nonmanifoldEdges':nonmanifold})
chain=[obj for obj in root.children_recursive if obj.type=='MESH' and obj.name.startswith('Drive chain')]
vertices=[];faces=[]
for obj in chain:
    base=len(vertices);vertices.extend(obj.matrix_world@vertex.co for vertex in obj.data.vertices)
    faces.extend(tuple(base+i for i in face.vertices) for face in obj.data.polygons)
chain_tree=BVHTree.FromPolygons(vertices,faces,all_triangles=False,epsilon=0)
chain_contacts=[]
obstacle_prefixes=['Upper black frame rail','Lower cradle frame','Seat triangle diagonal','Rear swingarm','Shock',
    'Frame transverse bridge','Triangular side cover','Swept connected header','Satin stacked silencer','Dark silencer outlet',
    'Silencer connected hanger','Collector perforated heat shield','Silencer perforated front guard','Rear genuinely perforated brake rotor','Rear brake caliper']
obstacles=[obj for obj in root.children_recursive if obj.type=='MESH' and
    (obj.name.startswith('V2 ') or any(obj.name.startswith(prefix) for prefix in obstacle_prefixes))]
for obj in obstacles:
    if not any(word in obj.name for word in ['tank','saddle','cushion','strap']):
        count=len(chain_tree.overlap(tree(obj)))
        if count:chain_contacts.append({'name':obj.name,'surfaceIntersections':count})
tank=bpy.data.objects['V2 copper teardrop tank'];tank_tree=tree(tank)
tank_contacts=[]
for name in ['Steering head','Upper triple clamp','Lower triple clamp','Upper black frame rail -1','Upper black frame rail 1']:
    count=len(tank_tree.overlap(tree(bpy.data.objects[name])))
    if count:tank_contacts.append({'name':name,'surfaceIntersections':count})
points=[obj.matrix_world@vertex.co for obj in root.children_recursive if obj.type=='MESH' for vertex in obj.data.vertices]
low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
contacts=[{'name':obj.name,'position':list(obj.matrix_world.translation)} for obj in root.children_recursive if obj.name.startswith('Contact_') or obj.name.startswith('Ground_') or obj.name.endswith('_Wheel_Front') or obj.name.endswith('_Wheel_Rear')]
print('SPARK_V2_AUDIT='+json.dumps({'newMeshCount':len(new_objects),'geometryIssues':rows,'chainObstacleCount':len(obstacles),'chainIntersections':chain_contacts,
    'tankContactsWithNamedStructure':tank_contacts,'bounds':[low,high],'contacts':contacts,'visualAccepted':False,
    'scope':'Named static mesh surface checks; mesh bounds and zero intersections do not prove swept clearance or visual fidelity.'}))
