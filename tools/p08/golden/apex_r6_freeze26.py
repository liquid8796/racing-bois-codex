import bpy
import json
ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/R6/RB_Golden_Apex_r6_editable26.blend')
scene=bpy.context.scene;root=bpy.data.objects['RB_Golden_Apex_r6']
assert root.get('visualAccepted')==False
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
before=bpy.data.is_dirty
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_checkpoint26_review.blend')
print('R6_FROZEN='+json.dumps({'source':bpy.data.filepath,'isDirtyBeforeSnapshot':before,'isDirtyAfterSnapshot':bpy.data.is_dirty,'objects':len(scene.objects),'root':root.name,'rootPhase':root.get('r6Phase'),'camera':{'name':scene.camera.name,'type':scene.camera.data.type,'lens':scene.camera.data.lens,'position':list(scene.camera.location),'rotation':list(scene.camera.rotation_euler)},'renderPath':scene.render.filepath,'resolution':[scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage],'engine':scene.render.engine,'samples':scene.cycles.samples,'threads':scene.render.threads,'visualAccepted':False,'exportedToAssets':False}))
