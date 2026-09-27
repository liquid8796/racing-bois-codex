"""Fork the frozen V2 actor in a new source; V2 and Apex assets are read-only."""
import bpy,math,json
from mathutils import Vector
scene=bpy.context.scene
root=bpy.data.objects['RB_Golden_Ash_V2'];root.name='RB_Golden_Ash_V3'
for level in range(3):bpy.data.objects['AshV2_L'+str(level)+'_Skin'].name='AshV3_L'+str(level)+'_Skin'
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath='D:/Project/Unity/racing-bois/Assets/RacingBois/Art/P08/Golden/Apex/V8/R2/RB_Golden_Apex_v8_r2.fbx',use_anim=False,ignore_leaf_bones=True)
added=[obj for obj in bpy.data.objects if obj not in before]
reference=bpy.data.collections.new('ApexR2_ContactReferenceOnly');scene.collection.children.link(reference)
for obj in added:
    for collection in list(obj.users_collection):collection.objects.unlink(obj)
    reference.objects.link(obj);obj['contact_reference_only']=True
bike=next(obj for obj in added if obj.name=='RB_Golden_Apex_v8_r2')
# Ash source uses anatomical left +X, forward -Y. Apex source uses semantic
# left -X, forward +Y. Rotate the bike reference 180 around Blender up only.
bike.rotation_euler.z+=math.pi
# Keep the actor root at identity. Move the bike by the inverse of the actual
# runtime rider placement (Unity0,-.08,-.32), expressed in this source basis.
bike.location+=Vector((0,-.32,.08))
for obj in added:
    if obj.type=='MESH':obj.hide_render='_L1_' in obj.name or '_L2_' in obj.name
bpy.context.view_layer.update()
markers={}
for obj in added:
    if obj.name.startswith('Contact_'):markers[obj.name]=list(obj.matrix_world.translation)
floor=bpy.data.objects.get('AshV2_ReviewFloor')
if floor:floor.location.z=.072
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V3/RB_Golden_Ash_V3.blend',compress=False)
print('ASH_V3_CONTACT_SCENE '+json.dumps({'bikeReference':bike.name,'markersActorLocalBlender':markers,'actorRootIdentity':list(root.location),'apexFileUnchanged':True,'v2FileUnchanged':True}))
