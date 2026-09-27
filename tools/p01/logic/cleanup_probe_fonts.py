"""Clean only font resources registered from this newly-created probe copy.

Early native probes used original AddFontResourceA. Later probes replace it
with FR_PRIVATE registration. This bounded cleanup never targets originals or
installed font files, and removes no file or registry key.
"""
import ctypes
import json
from pathlib import Path
from native_project import OUT

root=Path(__file__).resolve().parent
copy=(root/'runtime-copy').resolve()
assert copy.parent==root.resolve()
remove=ctypes.windll.gdi32.RemoveFontResourceW
remove.argtypes=[ctypes.c_wchar_p];remove.restype=ctypes.c_int
rows=[]
for name in ['BADLOC.DLL','FUTB.DLL','FUTD.DLL','FUTR.DLL']:
    path=(copy/'TEXT'/name).resolve()
    assert copy in path.parents and path.is_file()
    removed=0
    while removed<32 and remove(str(path)):removed+=1
    still_present=bool(remove(str(path))) if removed==32 else False
    rows.append({'task_owned_path':str(path),'registration_refs_removed':removed,'remaining_ref_detected':still_present})
assert not any(r['remaining_ref_detected'] for r in rows)
(OUT/'native-font-cleanup.json').write_text(json.dumps({'kind':'temporary task-copy font resource cleanup','files_deleted':0,'registry_keys_modified':0,'rows':rows},indent=2)+'\n')
print(json.dumps(rows,indent=2))
