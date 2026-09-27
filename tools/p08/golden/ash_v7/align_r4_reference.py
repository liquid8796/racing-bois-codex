import bpy,json,math
from mathutils import Matrix,Vector
root=bpy.data.objects['RB_Golden_Apex_r4'];root.matrix_world=Matrix.Translation(Vector((-.30,-.25,0)))@Matrix.Rotation(math.pi,4,'Z');bpy.context.view_layer.update();rows=[]
for o in root.children_recursive:
 if o.type!='EMPTY':continue
 p=o.matrix_world.translation;unity=Vector((-.30-p.x,p.z,-.25-p.y));rows.append({'name':o.name,'inAshBlender':list(p),'reconstructedUnityWorld':list(unity)})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_R4_ALIGNMENT '+json.dumps({'bikeUnityRoot':[0,0,0],'actorUnityRoot':[-.30,0,-.25],'actorRootYaw':0,'actorModelYaw':180,'ashBlenderToUnity':'(-.30-x,z,-.25-y)','bikeInAshAuthorSpace':'Translation(-.30,-.25,0) * Rz(180deg)','markers':rows}))
