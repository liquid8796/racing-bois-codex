"""Compose a read-only safe-mode audit for the current Blender scene."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('asset', choices=['traffic', 'patrol', 'rider', 'motorcycle'])
args = parser.parse_args()
folder = Path(__file__).resolve().parent
root = folder.parents[2]
names = {
    'traffic': ['RB_P06_TrafficCoupe', 'RB_P06_TrafficVan'],
    'patrol': ['RB_P06_PoliceMotorcycle'],
    'rider': ['RB_P06_Rider'],
    'motorcycle': ['RB_P06_Motorcycle'],
}[args.asset]
source = (folder / 'audit.py').read_text(encoding='utf8').rsplit('\nprint(', 1)[0]
source += '\nreports=[]\n'
for name in names:
    source += f'reports.append(audit(bpy.data.objects[{name!r}]))\n'
source += "print(json.dumps({'passed':all(r['passed'] for r in reports),'assets':reports}))\n"
destination = root / '_local' / ('p06-' + args.asset + '-audit.py')
destination.write_text(source, encoding='utf8')
print(destination)
