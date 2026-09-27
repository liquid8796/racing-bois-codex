import bpy,json
from mathutils import Vector
scene=bpy.context.scene;root=bpy.data.objects['RB_Golden_MenuEnvironment'];floor=bpy.data.objects['Menu_L0_Pullout']
for obj in root.children_recursive:
    if obj.type=='MESH':obj.hide_set('_L0_' not in obj.name);obj.hide_render='_L0_' not in obj.name
hit,point,normal,index=floor.ray_cast(Vector((0,0,5)),Vector((0,0,-1)))
print('MENU_STANDING_PLANE '+json.dumps({'hit':hit,'heightAtOriginMetres':point.z if hit else None,'upNormal':list(normal),'suggestedScenePlacementY':-point.z if hit else None,'groundMarkerAtOrigin':True,'note':'Actor pose/contact remains a root Unity review; no production acceptance.'}))
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/menu-environment/v1/composition-final.png'
bpy.ops.render.render(write_still=True)
