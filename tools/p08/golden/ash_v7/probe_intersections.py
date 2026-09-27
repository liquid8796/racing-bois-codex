import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_MenuHero'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update();o=bpy.data.objects['AshV7_L0_Skin'];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();points=[v.co for v in m.vertices]
skin=[p for p in m.polygons if m.materials[p.material_index].name=='AshV6_Skin_Baked'];ids=set(o['v7_collar_vertices'])|set(o['v7_facing_vertices']);collar=[p for p in m.polygons if all(i in ids for i in p.vertices)];tree=BVHTree.FromPolygons(points,[tuple(p.vertices) for p in skin],all_triangles=False);ctree=BVHTree.FromPolygons(points,[tuple(p.vertices) for p in collar],all_triangles=False);pairs=ctree.overlap(tree);index=set(a for a,b in pairs);rows=[]
for i in sorted(index):
 p=collar[i];center=sum((points[k] for k in p.vertices),Vector())/len(p.vertices);near,n,j,d=tree.find_nearest(center);rows.append({'face':p.index,'role':m.materials[p.material_index].name,'vertices':list(p.vertices),'restCenter':list(sum((o.data.vertices[k].co for k in p.vertices),Vector())/len(p.vertices)),'centroidSignedDistance':(center-near).dot(n),'area':p.area})
ev.to_mesh_clear();print('ASH_V7_COLLAR_INTERSECTIONS '+json.dumps({'pairs':len(pairs),'uniqueFaces':rows}))
