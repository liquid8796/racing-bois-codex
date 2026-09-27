"""Isolated second V8 candidate; preserves the entire Unity-rejected first one."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
T=ROOT/'tools/p08/golden'
source=(T/'apex_v8_model.py').read_text(encoding='utf8')
a=source.index('"""Bespoke body skins.')
b=source.index('# Aluminium twin spar chassis')
source=source[:a]+(T/'apex_v8_r2_surfaces.py').read_text(encoding='utf8')+'\n'+source[b:]
source=source.replace('/Apex/V8/', '/Apex/V8/R2/').replace('/apex/v8/', '/apex/v8/r2/').replace('RB_Golden_Apex_v8', 'RB_Golden_Apex_v8_r2')
source=source.replace("modifier.width=bevel;modifier.segments=3", "modifier.width=bevel;modifier.segments=2")
source=source.replace("bpy.ops.object.select_all(action='SELECT')\nbpy.ops.object.delete(use_global=False)", "for old_object in list(bpy.data.objects):\n    bpy.data.objects.remove(old_object,do_unlink=True)")
lines=[]
for line in source.splitlines():
    if "tube('Main box spar upper'" in line:line='    frame_spar(side)'
    if "tube('Box spar machined edge'" in line:line=line.replace(".012,'Apex_Machined'", ".004,'Apex_Graphite'")
    if "tube('Subframe triangulation'" in line:line=line.replace("'Apex_Machined'", "'Apex_Graphite'")
    if "rod('Axle clamp'" in line:line='    cast_fork_lower(side)'
    lines.append(line)
source='\n'.join(lines)+'\n'
(T/'apex_v8_r2_model.py').write_text(source,encoding='utf8')
textures=(T/'apex_v8_textures.py').read_text(encoding='utf8').replace('/Apex/V8\'', '/Apex/V8/R2\'')
(T/'apex_v8_r2_textures.py').write_text(textures,encoding='utf8')
for src,dst in [('apex_v8_finalize.py','apex_v8_r2_finalize.py'),('apex_v8_studio.py','apex_v8_r2_studio.py')]:
    s=(T/src).read_text(encoding='utf8').replace('/Apex/V8/', '/Apex/V8/R2/').replace('/apex/v8/', '/apex/v8/r2/').replace('RB_Golden_Apex_v8','RB_Golden_Apex_v8_r2')
    (T/dst).write_text(s,encoding='utf8')
descriptor=(T/'apex_v8_descriptor.py').read_text(encoding='utf8')
descriptor=descriptor.replace("EVIDENCE=ROOT/'docs/p08/golden/apex/v8'", "EVIDENCE=ROOT/'docs/p08/golden/apex/v8/r2'")
descriptor=descriptor.replace('/Apex/V8/', '/Apex/V8/R2/').replace('RB_Golden_Apex_v8','RB_Golden_Apex_v8_r2').replace('APEX_V8_GEOMETRY_AUDIT','APEX_V8_R2_GEOMETRY_AUDIT')
descriptor=descriptor.replace("bound('docs/p08/golden/apex/v8/descriptor.json')", "bound('docs/p08/golden/apex/v8/r2/descriptor.json')")
start=descriptor.index("audit['exactInputs']")
end=descriptor.index("\naudit['descriptor']",start)
inputs=['apex_v8_r2_prepare.py','apex_v8_r2_surfaces.py','apex_v8_r2_model.py','apex_v8_r2_textures.py','apex_v8_r2_finalize.py','apex_v8_r2_cap_repair.py','apex_v8_r2_studio.py','apex_v8_r2_audit.py']
descriptor=descriptor[:start]+"audit['exactInputs']=[asset['concept'],asset['conceptReview'],asset['source'],asset['fbx']]+[bound('tools/p08/golden/'+file) for file in "+repr(inputs)+"]"+descriptor[end:]
(T/'apex_v8_r2_descriptor.py').write_text(descriptor,encoding='utf8')
print('Isolated V8/R2 literal scripts prepared; V8/R1 source/export untouched.')
