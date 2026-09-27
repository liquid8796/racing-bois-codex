import bpy,json
from mathutils import Vector
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend',load_ui=False,use_scripts=False)
scene=bpy.context.scene
scene.blendermcp_auto_start_server=False
root=bpy.data.objects['RB_Golden_Spark_v1']
prefixes=['Lower cast','Cylinder','Cooling','Rounded cast','Inset cast','Recessed timing','Crankcase','Case bolt','Rear intake','Carburettor','Fuel line','Spark-plug','Copper teardrop','Long ribbed','Fitted black seat','Saddle','Passenger','Tank filler','Flush silver','Head cover','Engine','Cradle','Upper black frame','Frame']
objects=[]
for obj in root.children_recursive:
    if obj.type=='EMPTY' or any(obj.name.startswith(prefix) for prefix in prefixes):
        points=[obj.matrix_world@Vector(corner) for corner in obj.bound_box] if obj.type=='MESH' else [obj.matrix_world.translation]
        objects.append({'name':obj.name,'type':obj.type,'group':obj.get('asset_group'),'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]})
print('SPARK_V2_SOURCE='+json.dumps({'source':bpy.data.filepath,'root':root.name,'objects':objects,'safeAutoScripts':not bpy.context.preferences.filepaths.use_scripts_auto_execute,'sourceSaved':False}))
