"""Stage CC0 anatomical mesh DATA as an OBJ for allowed Blender MCP import.

This executes no MPFB addon code. Numeric target deltas are combined as asset
data; the upstream base topology, UVs and licenses retain explicit provenance.
"""
from pathlib import Path
import gzip,hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[3]
UPSTREAM=ROOT/'_local/mpfb2'
DATA=UPSTREAM/'src/mpfb/data'
OUT=ROOT/'ArtSource/P08/Golden/Ash/AnatomyV1'
OUT.mkdir(parents=True,exist_ok=True)
targets={
 'macrodetails/caucasian-male-young.target.gz':1.0,
 'macrodetails/universal-male-young-averagemuscle-averageweight.target.gz':0.72,
 'macrodetails/universal-male-young-maxmuscle-averageweight.target.gz':0.28,
 'head/head-square.target.gz':0.14,
 'chin/chin-width-incr.target.gz':0.23,
 'chin/chin-prominent-incr.target.gz':0.13,
 'chin/chin-bones-incr.target.gz':0.12,
 'nose/nose-hump-incr.target.gz':0.08,
 'nose/nose-scale-depth-incr.target.gz':0.13,
 'nose/nose-point-width-decr.target.gz':0.08,
 'eyebrows/eyebrows-trans-down.target.gz':0.06,
 'cheek/l-cheek-bones-incr.target.gz':0.10,
 'cheek/r-cheek-bones-incr.target.gz':0.10,
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lines=(DATA/'3dobjs/base.obj').read_text(encoding='utf-8').splitlines()
vertices=[list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')]
inventory=[]
for name,weight in targets.items():
    path=DATA/'targets'/name
    for line in gzip.decompress(path.read_bytes()).decode('utf-8').splitlines():
        if not line or line.startswith('#'):continue
        index,dx,dy,dz=line.split()
        for axis,value in enumerate([dx,dy,dz]):vertices[int(index)][axis]+=float(value)*weight
    inventory.append({'path':name,'sha256':sha(path),'weight':weight})
body_min=min(v[1] for v in vertices[:13380])
body_max=max(v[1] for v in vertices[:13380])
scale=1.78/(body_max-body_min)
staged=['# Racing Bois Ash anatomy candidate; MakeHuman CC0 topology derivative.',
        '# See provenance.json. This is a base, not a completed or accepted Ash.']
staged += [f'v {v[0]*scale:.9f} {(v[1]-body_min)*scale:.9f} {v[2]*scale:.9f}' for v in vertices]
staged += [l for l in lines if l.startswith('vt ')]
group=None
for line in lines:
    if line.startswith('g '):group=line[2:]
    elif group=='body' and line.startswith('f '):staged.append(line)
destination=OUT/'RB_Ash_AnatomicalBase.obj'
destination.write_text('\n'.join(staged)+'\n',encoding='utf-8')
for name in ['LICENSE.ASSETS.md','LICENSE.md']:
    shutil.copy2(UPSTREAM/name,OUT/name)
receipt={
 'status':'staged-anatomical-base-not-final-ash',
 'upstream':'https://github.com/makehumancommunity/mpfb2',
 'commit':'3edf9df0551765be43563d047888cf7877eb89b4',
 'asset_license':'CC0-1.0',
 'addon_executed':False,
 'upstream_base_sha256':sha(DATA/'3dobjs/base.obj'),
 'concept':'ArtSource/Concepts/P08/Golden/ash-v2.png',
 'concept_sha256':sha(ROOT/'ArtSource/Concepts/P08/Golden/ash-v2.png'),
 'target_datasets':inventory,
 'height_m':1.78,'obj_sha256':sha(destination),
 'note':'Numeric data conversion only. Garment, face likeness, materials, rigging and fidelity acceptance remain unfinished.'}
(OUT/'provenance.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'staged':str(destination),'sha256':sha(destination),'body_height':1.78,'targets':len(targets)}))
