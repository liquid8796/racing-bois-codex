"""Read-only same-flank chain/mechanism inspection, not whole-asset acceptance."""
import bpy
import bmesh
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root=bpy.data.objects['RB_Golden_Spark_v1']
bpy.context.view_layer.update()
chain=[o for o in root.children_recursive if o.type=='MESH' and o.name.startswith('Drive chain')]
prefixes=['Upper black frame rail','Lower cradle frame','Seat triangle diagonal','Rear swingarm',
          'Frame transverse bridge','Triangular side cover','Swept connected header','Satin stacked silencer',
          'Dark silencer outlet','Silencer rear frame hanger','Silencer connected hanger','Collector perforated heat shield','Silencer perforated front guard','Rear genuinely perforated brake rotor',
          'Rear brake caliper','Lower cast crankcase','Rounded crankcase lid','Inset cast service face']
obstacles=[o for o in root.children_recursive if o.type=='MESH' and any(o.name.startswith(p) for p in prefixes)]

vertices=[];faces=[]
for obj in chain:
    base=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
    faces.extend(tuple(base+i for i in face.vertices) for face in obj.data.polygons)
chain_bvh=BVHTree.FromPolygons(vertices,faces,all_triangles=False,epsilon=0)
chain_min=[min(p[i] for p in vertices) for i in range(3)]
chain_max=[max(p[i] for p in vertices) for i in range(3)]
rows=[]
for obj in obstacles:
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
    tree=BVHTree.FromPolygons(points,[tuple(face.vertices) for face in obj.data.polygons],all_triangles=False,epsilon=0)
    overlap=chain_bvh.overlap(tree)
    sampled=float('inf')
    for p in points:
        hit=chain_bvh.find_nearest(p)
        if hit[0] is not None:sampled=min(sampled,hit[3])
    separation=max(max(low[i]-chain_max[i],chain_min[i]-high[i]) for i in range(3))
    rows.append({'object':obj.name,'triangleSurfaceIntersections':len(overlap),
                 'positiveAabbAxisSeparationLowerBoundMetres':max(0,separation),
                 'minimumObstacleVertexToChainSampleMetres':sampled})

geometry=[]
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    data=obj.data;data.calc_loop_triangles();minimum=float('inf');bad=0
    for tri in data.loop_triangles:
        a,b,c=[obj.matrix_world@data.vertices[i].co for i in tri.vertices]
        area=(b-a).cross(c-a).length_squared;minimum=min(minimum,area);bad+=area<=1e-16
    bm=bmesh.new();bm.from_mesh(data);nonmanifold=sum(not edge.is_manifold for edge in bm.edges);bm.free()
    if bad or nonmanifold:geometry.append({'name':obj.name,'physicalTriangleFailures':bad,'nonManifoldEdges':nonmanifold,'minimumCrossSquared':minimum})
print('SPARK_CLEARANCE='+json.dumps({'chainBounds':[chain_min,chain_max],'chainComponents':len(chain),
      'sameVisibleFlankAsSilencers':True,'obstacles':rows,'geometryFailures':geometry,
      'scope':'Surface intersection checks for listed obstacles; sampled distances are not exact global clearances. Intentional roller/plate/sprocket contacts excluded. No full production or visual acceptance.'}))
