import bpy
assert '/Ash/V4/' in bpy.data.filepath.replace('\\','/')
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',load_ui=False,use_scripts=False)
print('REOPENED_SAVED_ASH_V4_AFTER_UNSAVED_DCC_FAILURE')
