import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=bpy.data.objects['RB_Golden_Apex_v8_r2'];old=root.location.copy();rows=[]
try:
    root.location=(-.32,-.13,0);bpy.context.view_layer.update()
    vertices=[];faces=[]
    for o in root.children_recursive:
        if o.type!='MESH' or '_L0_' not in o.name:continue
        start=len(vertices);vertices.extend([o.matrix_world@v.co for v in o.data.vertices]);faces.extend([tuple(start+i for i in p.vertices) for p in o.data.polygons])
    tree=BVHTree.FromPolygons(vertices,faces,all_triangles=False)
    for x in [-.22,-.18]:
        for y in [-.50,-.40,-.30,-.20,-.10,0,.10,.20,.30,.40,.50,.60]:
            p,n,index,d=tree.ray_cast(Vector((x,y,1.7)),Vector((0,0,-1)),1.5)
            if p is not None:rows.append({'x':x,'y':y,'surface':list(p),'normal':list(n)})
finally:root.location=old;bpy.context.view_layer.update()
print('ASH_MENU_CONTACT_PROBE '+json.dumps({'menuBikeRootBlender':[-.32,-.13,0],'equivalentActorOffsetUnity':[-.32,0,-.13],'samples':rows}))
