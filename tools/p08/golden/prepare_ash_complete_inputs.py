"""Stage licensed static anatomy/clothing data for the complete Ash candidate.

No MPFB code is imported or executed. This converts OBJ/MHCLO/target/weight
DATA into normal OBJ files and bounded plain numeric Blender operation batches.
"""
from pathlib import Path
from zipfile import ZipFile
from collections import defaultdict
import gzip,hashlib,json,shutil,math

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'_local/mpfb2/src/mpfb/data'
OUT=ROOT/'ArtSource/P08/Golden/Ash/V2'
TOOLS=ROOT/'tools/p08/golden/ash_v2'
EVIDENCE=ROOT/'docs/p08/golden/ash/v2'
for p in [OUT,TOOLS,EVIDENCE,OUT/'Inputs'] :p.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base_lines=(DATA/'3dobjs/base.obj').read_text().splitlines()
base=[list(map(float,l.split()[1:4])) for l in base_lines if l.startswith('v ')]
previous=json.loads((ROOT/'ArtSource/P08/Golden/Ash/AnatomyV1/provenance.json').read_text())
targets={x['path']:x['weight'] for x in previous['target_datasets']}
targets.update({'head/head-square.target.gz':.19,'head/head-rectangular.target.gz':.10,
 'chin/chin-width-incr.target.gz':.29,'chin/chin-bones-incr.target.gz':.31,
 'chin/chin-prominent-incr.target.gz':.18,'nose/nose-scale-depth-incr.target.gz':.23,
 'nose/nose-scale-vert-incr.target.gz':.08,'nose/nose-point-down.target.gz':.10,
 'eyebrows/eyebrows-trans-down.target.gz':.13,
 'cheek/l-cheek-bones-incr.target.gz':.29,'cheek/r-cheek-bones-incr.target.gz':.29,
 'cheek/l-cheek-volume-decr.target.gz':.12,'cheek/r-cheek-volume-decr.target.gz':.12})
inventory=[]
def numeric_target(path):
    out=[]
    for line in gzip.decompress(path.read_bytes()).decode().splitlines():
        if line and not line.startswith('#'):
            a,*xyz=line.split();out.append((int(a),list(map(float,xyz))))
    return out
for name,weight in targets.items():
    path=DATA/'targets'/name
    for i,xyz in numeric_target(path):
        for axis in range(3):base[i][axis]+=xyz[axis]*weight
    inventory.append({'target':name,'weight':weight,'sha256':sha(path)})
bottom=min(v[1] for v in base[:13380]);top=max(v[1] for v in base[:13380])
scale=1.78/(top-bottom)
base=[[v[0]*scale,(v[1]-bottom)*scale+.025,v[2]*scale] for v in base]

groups=json.loads((DATA/'mesh_metadata/basemesh_vertex_groups.json').read_text())
def joint(name):
    ids=[i for a,b in groups[name] for i in range(a,b+1)]
    return [sum(base[i][axis] for i in ids)/len(ids) for axis in range(3)]
joints={n:joint(n) for n in groups if n.startswith('joint-')}
upstream_weights=json.loads((DATA/'rigs/standard/weights.game_engine.json').read_text())['weights']
weights=[defaultdict(float) for _ in base]
def mapped_bone(name):
    if name in ('Root','pelvis'):return 'Hip'
    if name.startswith(('spine','clavicle')):return 'Torso'
    if name in ('head','neck_01'):return 'Head'
    side='L' if name.endswith('_l') else 'R'
    for prefix,role in [('upperarm','UpperArm'),('lowerarm','Forearm'),('thigh','Thigh'),('calf','Shin'),('foot','Foot'),('ball','Foot')]:
        if name.startswith(prefix):return role+'_'+side
    return 'Hand_'+side
for bone,pairs in upstream_weights.items():
    name=mapped_bone(bone)
    for i,weight in pairs:weights[i][name]+=weight
def normalized(values):
    values=sorted(((k,v) for k,v in values.items() if v>.00001),key=lambda p:-p[1])[:4]
    total=sum(v for _,v in values)
    return {k:round(v/total,6) for k,v in values} if total else {'Hip':1.0}
weights=[normalized(w) for w in weights]
def output_obj(name,vertices,lines,keep_body=False):
    result=['# CC0 topology derivative for Racing Bois Ash, see provenance.json.']
    result += ['v '+' '.join(f'{n:.9f}' for n in v) for v in vertices]
    result += [l for l in lines if l.startswith('vt ')]
    group=None
    for l in lines:
        if l.startswith('g '):group=l[2:]
        elif l.startswith('f ') and (not keep_body or group=='body'):result.append(l)
    p=OUT/'Inputs'/(name+'.obj');p.write_text('\n'.join(result)+'\n')
    inventory.append({'staged':p.relative_to(OUT).as_posix(),'sha256':sha(p),'vertices':len(vertices)})
    return p
output_obj('Body',base,base_lines,True)
objects={'Body':{'count':13380,'weights':weights[:13380]}}
archive=ROOT/'_local/mpfb-data/makehuman_system_assets_cc0.zip'
with ZipFile(archive) as z:
    for name,stem in [('Eyes','eyes/low-poly/low-poly'),('Brows','eyebrows/eyebrow001/eyebrow001'),
                      ('Hair','hair/short02/short02'),('Clothes','clothes/male_casualsuit02/male_casualsuit02'),
                      ('Shoes','clothes/shoes01/shoes01')]:
        rows=[];object_weights=[];active=False;factors=[1,1,1]
        for line in z.read(stem+'.mhclo').decode('utf-8').splitlines():
            values=line.split()
            if not values or line.startswith('#'):
                if not values:active=False
                continue
            if values[0] in ('x_scale','y_scale','z_scale'):
                axis={'x_scale':0,'y_scale':1,'z_scale':2}[values[0]]
                factors[axis]=abs(base[int(values[1])][axis]-base[int(values[2])][axis])/float(values[3])
            elif values[0]=='verts':active=True
            elif active and values[0].isdigit():
                if len(values)==1:
                    i=int(values[0]);rows.append(base[i]);object_weights.append(weights[i])
                elif len(values)==9:
                    indices=list(map(int,values[:3]));amounts=list(map(float,values[3:6]));offset=list(map(float,values[6:]))
                    rows.append([sum(base[i][axis]*w for i,w in zip(indices,amounts))+offset[axis]*factors[axis] for axis in range(3)])
                    combined=defaultdict(float)
                    for i,w in zip(indices,amounts):
                        for bone,weight in weights[i].items():combined[bone]+=weight*w
                    object_weights.append(normalized(combined))
                else:active=False
            elif active:active=False
        raw=z.read(stem+'.obj').decode('utf-8').splitlines()
        assert len(rows)==sum(l.startswith('v ') for l in raw),(name,len(rows))
        output_obj(name,rows,raw)
        objects[name]={'count':len(rows),'weights':object_weights}
        for extension in ('.obj','.mhclo'):
            payload=z.read(stem+extension)
            inventory.append({'archive_path':stem+extension,'sha256':hashlib.sha256(payload).hexdigest(),'license':'CC0-1.0'})
    for path in ['skins/young_caucasian_male/young_lightskinned_male_diffuse.png',
                 'eyes/materials/brown_eye.png','eyebrows/eyebrow001/eyebrow001.png',
                 'hair/short02/short02_diffuse.png','hair/short02/short02_normal.png',
                 'clothes/male_casualsuit02/male_casualsuit02_normal.png',
                 'clothes/shoes01/shoes01_normal.png']:
        p=OUT/'Inputs'/Path(path).name;p.write_bytes(z.read(path))
        inventory.append({'archive_path':path,'staged':p.relative_to(OUT).as_posix(),'sha256':sha(p),'license':'CC0-1.0'})

# Numeric weights are sent in independent bounded batches; no disk reader or
# addon code is smuggled into Blender's safe-mode operation scripts.
for name,entry in objects.items():
    for offset in range(0,entry['count'],2500):
        payload=[[i,list(entry['weights'][i].items())] for i in range(offset,min(offset+2500,entry['count']))]
        encoded=json.dumps(payload,separators=(',',':'))
        script=f'''import bpy,json
obj=bpy.data.objects['AshV2_{name}']
assert len(obj.data.vertices)=={entry['count']}
rows=json.loads({encoded!r})
for index,values in rows:
    for bone,amount in values:
        group=obj.vertex_groups.get('RB_P06_Rider_L0_'+bone)
        if group is None:group=obj.vertex_groups.new(name='RB_P06_Rider_L0_'+bone)
        group.add([index],amount,'REPLACE')
print('ASH_V2_WEIGHT_BATCH {name} {offset} '+str(len(rows)))
'''
        assert len(script.encode())<200000
        (TOOLS/f'weights_{name}_{offset:05d}.py').write_text(script)

expressions={}
for label,parts in {'Happy':{'mouth-corner-puller':.5},'Focused':{'eyebrows-left-down':.55,'eyebrows-right-down':.55}}.items():
    values=defaultdict(lambda:[0,0,0])
    for name,weight in parts.items():
        path=DATA/'targets/expression/units/caucasian'/(name+'.target.gz')
        inventory.append({'expression_target':name,'sha256':sha(path),'weight':weight})
        for i,delta in numeric_target(path):
            if i<13380:
                for a in range(3):values[i][a]+=delta[a]*scale*weight
    expressions[label]=[[i,[v[0],-v[2],v[1]]] for i,v in values.items()]
encoded=json.dumps(expressions,separators=(',',':'))
(TOOLS/'expressions.py').write_text(f'''import bpy,json
from mathutils import Vector
obj=bpy.data.objects['AshV2_Body']
obj.shape_key_clear()
obj.shape_key_add(name='Basis',from_mix=False)
values=json.loads({encoded!r})
for name,rows in values.items():
    key=obj.shape_key_add(name=name,from_mix=False)
    key.value=0
    for i,delta in rows:key.data[i].co+=Vector(delta)
print('ASH_V2_EXPRESSIONS '+str(list(values)))
''')
(OUT/'anatomy-joints.json').write_text(json.dumps(joints,indent=2)+'\n')
for n in ['LICENSE.ASSETS.md','LICENSE.md']:shutil.copy2(ROOT/'_local/mpfb2'/n,OUT/n)
provenance={'status':'unaccepted-complete-candidate-in-progress','concept_sha256':sha(ROOT/'ArtSource/Concepts/P08/Golden/ash-v2.png'),
            'upstream_commit':'3edf9df0551765be43563d047888cf7877eb89b4','system_archive_sha256':sha(archive),'asset_license':'CC0-1.0',
            'addon_code_executed':False,'source_topology':'MakeHuman anatomical and selected clothing base data; custom Ash modeling follows.',
            'inputs':inventory,'object_vertex_counts':{k:v['count'] for k,v in objects.items()}}
(OUT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(provenance['object_vertex_counts']))
