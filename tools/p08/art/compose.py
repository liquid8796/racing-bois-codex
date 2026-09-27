"""Compose literal recipes for the pinned Blender MCP safe-mode interpreter.

The shared geometry/UV exporter is Racing Bois original P06 authoring code.
No recipe uses exec, eval, operating-system calls, or external asset services.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('batch', choices=['neon', 'ridge', 'coast', 'orchard', 'bikes', 'riders', 'traffic', 'support'])
parser.add_argument('--indices', default='1,2,3,4,5')
args = parser.parse_args()
for directory in ['ArtSource/P08', 'Assets/RacingBois/Art/P08', 'docs/p08/art']:
    (ROOT / directory).mkdir(parents=True, exist_ok=True)
common = (ROOT / 'tools/p06/hero/common.py').read_text(encoding='utf8')
common = common.replace("OUT=ROOT+'Assets/RacingBois/Art/P06/Hero/'", "OUT=ROOT+'Assets/RacingBois/Art/P08/'")
common = common.replace("ROOT+'_local/p06-before-'", "ROOT+'_local/p08-before-'")
common = common.replace('grain=math.sin(x*2.17+math.sin(y*.53))*math.cos(y*2.33+x*.12)', 'grain=procedural_grain(x,y,dim,surface)')
common = common.replace('relief=grain*.015', "relief=grain*(.16 if surface=='concrete' else .11 if surface=='wood' else .075 if surface=='foliage' else .015)")
recipe = 'environments.py' if args.batch in ['neon', 'ridge', 'coast', 'orchard'] else args.batch + '.py'
source = common + '\nBATCH=' + repr(args.batch) + '\n'
source += 'SELECTED_INDICES=' + repr([int(i) for i in args.indices.split(',')]) + '\n'
source += (ROOT / 'tools/p08/art/common.py').read_text(encoding='utf8') + '\n'
source += (ROOT / 'tools/p08/art' / recipe).read_text(encoding='utf8')
target = ROOT / '_local' / ('p08-' + args.batch + '-recipe.py')
target.write_text(source, encoding='utf8')
print(target)
