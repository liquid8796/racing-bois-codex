import bpy,json
ROOT='D:/Project/Unity/racing-bois/';before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=ROOT+'Assets/RacingBois/Art/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4.fbx',use_anim=False,use_image_search=False)
created=list(set(bpy.data.objects)-before);collection=bpy.data.collections.new('ApexR4_ContactReferenceOnly');bpy.context.scene.collection.children.link(collection)
for o in created:
 for old in list(o.users_collection):old.objects.unlink(o)
 collection.objects.link(o)
roots=[o for o in created if o.parent not in created];rows=[]
for o in created:
 if o.type=='EMPTY':rows.append({'name':o.name,'world':list(o.matrix_world.translation),'rotation':list(o.rotation_euler),'scale':list(o.scale)})
for o in roots:o['ash_v7_contact_reference']=True
collection.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_R4_IMPORT '+json.dumps({'roots':[o.name for o in roots],'empties':rows,'meshObjects':len([o for o in created if o.type=='MESH']),'referenceOnly':True}))
