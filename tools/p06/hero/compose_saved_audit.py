"""Compose a literal read-only audit of saved hero sources for real Blender MCP."""
from pathlib import Path

folder = Path(__file__).resolve().parent
root = folder.parents[2]
source = (folder / 'audit.py').read_text(encoding='utf8').rsplit('\nprint(', 1)[0]
source += '\nreports=[]\n'
for name in ['RB_P06_Motorcycle', 'RB_P06_Rider', 'RB_P06_TrafficCoupe',
             'RB_P06_TrafficVan', 'RB_P06_PoliceMotorcycle']:
    path = (root / 'ArtSource/P06/Hero' / (name + '.blend')).as_posix()
    source += f'bpy.ops.wm.open_mainfile(filepath={path!r}, load_ui=False, use_scripts=False)\n'
    source += f'report=audit(bpy.data.objects[{name!r}])\n'
    source += f'report["source"]={path!r}\n'
    source += 'reports.append(report)\n'
source += "print(json.dumps({'passed':all(r['passed'] for r in reports),'assets':reports,'scope':'Saved authored Blender meshes; no sources saved or exported during audit.'}))\n"
destination = root / '_local/p06-saved-hero-audit.py'
destination.write_text(source, encoding='utf8')
print(destination)
