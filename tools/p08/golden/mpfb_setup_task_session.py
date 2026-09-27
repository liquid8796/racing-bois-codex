"""Load pinned MPFB only into the task-owned Blender session.

Registration uses Blender's local extension repository and addon API. User
preferences are not saved; MPFB data/logs stay under the repository's _local.
This script does not create characters or perform external service requests.
"""
import bpy,importlib,json
from pathlib import Path

ROOT=Path('D:/Project/Unity/racing-bois')
data_root=ROOT/'_local/mpfb-user'
data_root.mkdir(parents=True,exist_ok=True)
preferences=bpy.context.preferences
preferences.use_preferences_save=False
module='bl_ext.racing_bois_task.mpfb'
repos=preferences.extensions.repos
repo=next((r for r in repos if r.module=='racing_bois_task'),None)
if repo is None:
    repo=repos.new(name='Racing Bois task local MPFB',module='racing_bois_task',custom_directory=str(ROOT/'_local/mpfb2/src'))
repo.use_remote_url=False
package=importlib.import_module(module)
preference_module=importlib.import_module(module+'._preferences')
if module not in preferences.addons:
    bpy.utils.register_class(preference_module.MpfbPreferences)
    entry=preferences.addons.new()
    entry.module=module
else:
    entry=preferences.addons[module]
entry.preferences.mpfb_user_data=str(data_root)
entry.preferences.mh_auto_user_data=False
result=bpy.ops.preferences.addon_enable(module=module)
LocationService=importlib.import_module(module+'.services.locationservice').LocationService
actual_data=Path(LocationService.get_user_data()).resolve()
assert actual_data.is_relative_to(data_root.resolve())
print(json.dumps({'setup':list(result),'version':package.VERSION,'module':module,
                  'data_root':str(actual_data),'preferences_saved':False,
                  'scene_unchanged':bpy.data.filepath,'external_generation':False}))
