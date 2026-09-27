import bpy,json
from mathutils.bvhtree import BVHTree
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_MenuHero'];scene.frame_set(1);bpy.context.view_layer.update();bike=bpy.data.objects['RB_Golden_Apex_r4'];points=[];faces=[];info=[]
for obj in bike.children_recursive:
 if obj.type!='MESH' or not obj.name.startswith('Apex_L0_'):continue
 start=len(points);points.extend([obj.matrix_world@v.co for v in obj.data.vertices]);faces.extend([tuple(start+i for i in p.vertices) for p in obj.data.polygons]);info.extend([{'object':obj.name,'polygon':p.index,'material':obj.data.materials[p.material_index].name} for p in obj.data.polygons])
tree=BVHTree.FromPolygons(points,faces,all_triangles=False);obj=bpy.data.objects['AshV7_L0_Skin'];ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();rows=[]
for v in obj.data.vertices:
 if not any((obj.vertex_groups[g.group].name=='RB_P06_Rider_L0_Hand_L' or ('Finger_' in obj.vertex_groups[g.group].name and obj.vertex_groups[g.group].name.endswith('_L'))) and g.weight>.15 for g in v.groups):continue
 point=m.vertices[v.index].co;p,n,index,d=tree.find_nearest(point);signed=(point-p).dot(n)
 if signed<0:rows.append({'vertex':v.index,'point':list(point),'nearest':list(p),'normal':list(n),'planeSigned':signed,'actualDistance':d,'referenceFace':info[index]})
ev.to_mesh_clear();print('ASH_V7_CONTACT_PLANE_DIAGNOSTIC '+json.dumps({'negativePlanePoints':rows,'note':'Negative distance to a nearest triangle plane is not automatically inside a closed volume near edges.'}))
