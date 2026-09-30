import bpy,json
from pathlib import Path
source=Path('D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_PreEdit.blend')
if bpy.data.filepath:
    raise RuntimeError('Only the freshly started factory scene may be replaced')
if bpy.context.preferences.filepaths.use_scripts_auto_execute:
    raise RuntimeError('Auto-execute must be disabled before reading the owned copy')
if set(bpy.data.objects.keys())!={'Camera','Cube','Light'}:
    raise RuntimeError('Fresh factory scene expected; preserve any unrelated scene')
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
if bpy.data.filepath.replace('\\','/')!=str(source) or bpy.context.preferences.filepaths.use_scripts_auto_execute:
    raise RuntimeError('Owned path/autoexec state differs')
scene=bpy.context.scene
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.cycles.device='CPU'
rig=bpy.data.objects.get('RB_P06_Rider_Rig')
def obj(o):
    return dict(name=o.name,type=o.type,hidden=o.hide_get(),hideRender=o.hide_render,
                parent=o.parent.name if o.parent else None,location=list(o.location),
                data=o.data.name if o.data else None)
print('ASH_V8_OWNED_OPEN '+json.dumps(dict(filepath=bpy.data.filepath,autoexecute=bpy.context.preferences.filepaths.use_scripts_auto_execute,
    frame=scene.frame_current,camera=scene.camera.name if scene.camera else None,engine=scene.render.engine,
    rig=obj(rig) if rig else None,action=rig.animation_data.action.name if rig and rig.animation_data and rig.animation_data.action else None,
    objects=[obj(o) for o in scene.objects if o.type!='MESH' or o.name.startswith('AshV7_L') or 'Hair' in o.name or 'Collar' in o.name],
    renderVisibleMeshes=[o.name for o in scene.objects if o.type=='MESH' and not o.hide_render],
    actions=[a.name for a in bpy.data.actions])))
