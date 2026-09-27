"""Open only the saved task-authored Ash source; embedded scripts are disabled."""
import bpy
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend',load_ui=False,use_scripts=False)
print('ASH_V2_SAVED_CANDIDATE_REOPENED')
