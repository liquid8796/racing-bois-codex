"""Independent audit of final saved P08 meshes over real Blender MCP."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
manifest=json.loads((ROOT/'Assets/RacingBois/Art/P08/ArtManifest.json').read_text(encoding='utf8'))
source=(ROOT/'tools/p06/hero/audit.py').read_text(encoding='utf8').rsplit('\nprint(',1)[0]
source=source.replace("return {'root':root.name,'passed':all(r['passed'] for r in reports)", "return {'root':root.name,'passed':bool(reports) and all(r['passed'] and r['triangles']>0 for r in reports)")
source+='\nreports=[]\n'
for path in sorted({a['source'] for a in manifest['assets']}):
    source+='bpy.ops.wm.open_mainfile(filepath='+repr((ROOT/path).as_posix())+', load_ui=False, use_scripts=False)\n'
    for asset in [a for a in manifest['assets'] if a['source']==path]:
        source+='report=audit(bpy.data.objects['+repr(asset['name'])+'])\n'
        source+='report["source"]='+repr(path)+'\nreports.append(report)\n'
source+="print(json.dumps({'passed':bool(reports) and all(r['passed'] for r in reports),'assets':reports,'scope':'Read-only independent audits of saved Blender sources; manifold/winding/positive-volume/UV/component-overlap/skin weights; no new sources saved or exported.'}))\n"
path=ROOT/'_local/p08-saved-art-audit.py';path.write_text(source,encoding='utf8');print(path)
