"""Install only reviewed C#/asmdef source; no Editor or process control."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
EXPECTED='af2903895a95adf9087cf307ae94c238f2943b9e1d16a7f00dafd2b083f6277d'
assert hashlib.sha256((HERE/'Editor/NativeProbeBuilder.cs').read_bytes()).hexdigest()==EXPECTED
target=ROOT/'Assets/RacingBois/Diagnostics/NativeProbe'
assert not target.exists(),'Preserve an existing installed diagnostic'
rows=[]
for directory in ('Runtime','Editor'):
    for source in sorted((HERE/directory).rglob('*')):
        if source.suffix not in ('.cs','.asmdef'):continue
        relative=source.relative_to(HERE);destination=target/relative
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        assert hashlib.sha256(destination.read_bytes()).hexdigest()==digest
        rows.append({'path':destination.relative_to(ROOT).as_posix(),'sha256':digest})
receipt=ROOT/'docs/p10/unity-native-probe-staging/installed-source.json'
receipt.write_text(json.dumps({'installed':True,'compiledInUnity':False,'files':rows},indent=2)+'\n')
print('INSTALLED_REVIEWED_NATIVE_PROBE',len(rows),'files; actual Unity compilation/build still required')
