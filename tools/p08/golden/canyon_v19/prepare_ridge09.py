"""Preserve failed08 and create09 with physical UV repair and bounded spur height."""
from pathlib import Path
import json,hashlib,ast
from blender_mcp.safe_mode import validate_code
b=Path('tools/p08/golden/canyon_v19');d=Path('docs/p08/golden/canyon/v19')
def row(p):
    p=Path(p);return {'path':p.as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
prior=json.loads((d/'candidate07-freeze-manifest.json').read_text(encoding='utf-8'))
for r in prior['files']+prior['protected']+prior['cc0AndMaterialInputs']:
    assert row(r['path'])['sha256']==r['sha256'],r['path']
files=[]
for base in ['ArtSource/P08/Golden/Canyon/V19',str(d),str(b)]:
    files.extend(p for p in Path(base).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
manifest={'schema':1,'candidate':'V19-08','authoringPassed':False,'sourceSaved':False,'actualRenderCreated':False,'visualAccepted':False,'exportedToAssets':False,'files':[row(p) for p in sorted(files)],'protected':prior['protected'],'cc0AndMaterialInputs':prior['cc0AndMaterialInputs']}
with (d/'candidate08-freeze-manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
s=(b/'author_ridge08.py').read_text(encoding='utf-8').replace("DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_08.blend'", "DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_09.blend'")
s=s.replace('                     -39,nominal-50-8*random_unit(group+29,seed)', '                     nominal-92 if nominal>120 else -39,nominal-50-8*random_unit(group+29,seed)')
s=s.replace('    uv_min=None;physical_min=None;seen=set();duplicates=0','    uv_min=None;physical_min=None;seen=set();duplicates=0;uv_repairs=[]')
needle="""        if not math.isfinite(physical) or physical<=1e-16 or not math.isfinite(cross) or abs(cross)<=1e-14:
            raise RuntimeError('Physical/primary UV triangle threshold failed: '+obj.name)"""
replacement="""        if math.isfinite(physical) and physical>1e-16 and math.isfinite(cross) and abs(cross)<=1e-14:
            # Reflected sampling can alias real corners. Project the physical
            # triangle with its actual aspect into a continuous source island.
            # No epsilon offsets or geometry edits are made.
            before_uv=[[float(v.x),float(v.y)] for v in uv]
            wp=[obj.matrix_world@mesh.vertices[i].co for i in triangle.vertices]
            ex=(wp[1]-wp[0]).normalized();ey=(wp[1]-wp[0]).cross(wp[2]-wp[0]).normalized().cross(ex)
            plane=[((p-wp[0]).dot(ex),(p-wp[0]).dot(ey)) for p in wp]
            u0=min(p[0] for p in plane);v0=min(p[1] for p in plane)
            extent=max(max(p[0] for p in plane)-u0,max(p[1] for p in plane)-v0)
            patch=CC0_PATCHES[0]['samples'];anchor=Vector(patch[3][7][1:])
            axis_u=Vector(patch[3][20][1:])-anchor;axis_v=Vector(patch[9][7][1:])-anchor
            for loop,point in zip(triangle.loops,plane):
                layer.data[loop].uv=anchor+axis_u*((point[0]-u0)/extent*.8)+axis_v*((point[1]-v0)/extent*.8)
            uv=[layer.data[i].uv for i in triangle.loops]
            cross=(float(uv[1].x)-uv[0].x)*(float(uv[2].y)-uv[0].y)-(float(uv[1].y)-uv[0].y)*(float(uv[2].x)-uv[0].x)
            uv_repairs.append({'vertices':list(triangle.vertices),'beforeUv':before_uv,'afterUv':[[float(v.x),float(v.y)] for v in uv],
                'physicalCrossSquared':physical,'afterUvCross':cross,'physicalProjectionExtentMetres':extent})
            if len(uv_repairs)>32:raise RuntimeError('Unexpectedly many source UV aliases; retain rejection.')
        if not math.isfinite(physical) or physical<=1e-16 or not math.isfinite(cross) or abs(cross)<=1e-14:
            raise RuntimeError('Physical/primary UV triangle threshold failed: '+obj.name)"""
assert needle in s;s=s.replace(needle,replacement)
s=s.replace("'materials':[mat.name for mat in mesh.materials],'minimumBlender':low", "'materials':[mat.name for mat in mesh.materials],'sourceUvAliasPhysicalProjections':uv_repairs,'minimumBlender':low")
s=s.replace("'uvPolicy':'Side UVs sampled from continuous originalCC0 islands; caps use physical2.4m projection. No epsilon UV offsets.'", "'uvPolicy':'Side UVs from continuous originalCC0 islands; exact sampling aliases use recorded physical triangle projection into source atlas. Caps physical2.4m. No epsilon offsets.'")
s=s.replace('RearCliffBelt_V19_08','RearCliffBelt_V19_09').replace('candidate08-gameplay','candidate09-gameplay').replace('CANYON_V19_RIDGE08','CANYON_V19_RIDGE09')
validate_code(s);ast.parse(s)
with (b/'author_ridge09.py').open('x',encoding='utf-8') as f:f.write(s)
r=(b/'render_candidate08.py').read_text(encoding='utf-8').replace('V19_08','V19_09').replace('candidate08','candidate09').replace('RENDER08','RENDER09')
with (b/'render_candidate09.py').open('x',encoding='utf-8') as f:f.write(r)
record={'schema':1,'failed08Freeze':row(d/'candidate08-freeze-manifest.json'),'actualParent':'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_07.blend','scope':'Rear belt retry with bounded spur height and true physical projection only for measured sourceUV aliases; strict thresholds unchanged','visualAccepted':False,'safeModePreflight':True}
with (d/'candidate09-inputs.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print(json.dumps({'08Freeze':row(d/'candidate08-freeze-manifest.json'),'09Script':row(b/'author_ridge09.py')},indent=2))
