"""Compose V3-only clip/export/audit recipes while retaining semantic bone names."""
from pathlib import Path
folder=Path(__file__).parent
source=(folder/'pose_library.py').read_text(encoding='utf-8')
tail=(folder.parent/'ash_v2/author_clips.tail.py').read_text(encoding='utf-8').replace('AshV2','AshV3').replace('Ash/V2','Ash/V3').replace('Ash_V2','Ash_V3')
tail=tail.replace('clip_receipt=[]',"viewport_state={obj:obj.hide_viewport for obj in bpy.data.objects if obj.type=='MESH'}\nfor obj in viewport_state:obj.hide_viewport=True\nclip_receipt=[]")
tail=tail.replace("rig.animation_data.action=None\nscene.frame_set(1)","for obj,value in viewport_state.items():obj.hide_viewport=value\nrig.animation_data.action=None\nscene.frame_set(1)")
(folder/'author_clips.py').write_text(source+tail,encoding='utf-8')
for filename in ['audit_runtime.py','export_frozen_runtime.py']:
    text=(folder.parent/'ash_v2'/filename).read_text(encoding='utf-8').replace('AshV2','AshV3').replace('Ash/V2','Ash/V3').replace('Ash_V2','Ash_V3')
    if filename=='export_frozen_runtime.py':
        text=text.replace("rig.animation_data.action=None","rig.animation_data_create();rig.animation_data.action=None")
    (folder/filename).write_text(text,encoding='utf-8')
print('V3-only recipes prepared; V2 inputs unmodified')
