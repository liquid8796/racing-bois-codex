"""Compose an explicit Blender MCP recipe; does not execute Blender code.

V8 keeps the existing authored manufactured chassis/wheel components only.
All visually dominant body skins are independently replaced from Apex v2.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
base = (ROOT / 'tools/p08/golden/apex_model_v7.py').read_text(encoding='utf8')
header = base[:base.index('# Bespoke broad, low sporting tank')]
header = header.replace("/V7/", "/V8/").replace("/v7/", "/v8/").replace("v7'", "v8'")
header = header.replace('return Vector((p[0], -p[2], p[1]))', 'return Vector((p[0], p[2], p[1]))')
header = header.replace("scene.cycles.samples = 24", "scene.cycles.samples = 24\nscene.cycles.device = 'CPU'\nscene.render.threads_mode = 'FIXED'\nscene.render.threads = 4")
header = header.replace("image = bpy.data.images.load(OUT + name + '_' + kind + '.png', check_existing=True)", "image = bpy.data.images.load(OUT + name + '_' + kind + '.png', check_existing=True)\n        image.reload()")
header = header.replace("shader.inputs['Transmission Weight'].default_value=.42", "shader.inputs['Transmission Weight'].default_value=.20")
header = header.replace("'Apex_RedLamp']:", "'Apex_RedLamp','Apex_Lens']:", 1)
header = header.replace("    if name in ['Apex_Lamp','Apex_RedLamp']:", "    if name=='Apex_Lens':\n        shader.inputs['Transmission Weight'].default_value=1.0\n        shader.inputs['IOR'].default_value=1.46\n    if name in ['Apex_Lamp','Apex_RedLamp']:")
header = header.replace("modifier.segments=2", "modifier.segments=3")
body = (ROOT / 'tools/p08/golden/apex_v8_surfaces.py').read_text(encoding='utf8')
mechanical = base[base.index('# Aluminium twin spar chassis'):base.index('# Candidate surfacing experiment')]
# The crown is narrower, the tail shell is lower and no body-wide stripe is
# copied from the former component setup. Chassis and wheel dimensions remain.
mechanical = mechanical.replace("('Front',.715,.118),('Rear',-.715,.183)", "('Front',.715,.130),('Rear',-.715,.190)")
mechanical = mechanical.replace(".0017,'Apex_Graphite',label,sides=4", ".0007,'Apex_Rubber',label,sides=4")
mechanical = mechanical.replace(".0095,'Apex_Graphite',label,sides=8", ".012,'Apex_Graphite',label,sides=8")
mechanical = mechanical.replace(".044,'Apex_Graphite',sides=6", ".030,'Apex_Graphite',sides=6")
mechanical = mechanical.replace(".013,'Apex_Machined',sides=10", ".010,'Apex_Machined',sides=10")
end = base[base.index('# Candidate surfacing experiment'):]
end = end.replace("APEX_V7_CANDIDATE", "APEX_V8_CANDIDATE")
end = end.replace("(.105,.12,.14,1)", "(.38,.40,.42,1)").replace("default_value=.35;scene.world", "default_value=.42;scene.world")
end = end.replace("(.095,.10,.115,1)", "(.30,.32,.34,1)")
end = end.replace("(2.85,1.52,3.45)", "(-3.6,1.42,3.30)")
end = end.replace("SOURCE+NAME+'.blend'", "SOURCE+NAME+'.blend'")
end = (ROOT/'tools/p08/golden/apex_v8_profile_refine.py').read_text(encoding='utf8') + '\n' + end
end = end.replace("# Neutral studio lighting.", "for obj in parts: obj['asset_group']='Body'\nfor key in ['Front','Rear']:\n    for obj in wheel_parts[key]: obj['asset_group']=key\n# Neutral studio lighting.")
end = end.replace("size=200", "size=2000")
end = end.replace("(-3.6,1.42,3.30)", "(3.6,1.42,3.30)")
recipe = header + body + '\n' + mechanical + '\n' + end
(ROOT / 'tools/p08/golden/apex_v8_model.py').write_text(recipe, encoding='utf8')

# These deterministic surfaces are original physical finish maps. Fresh files
# are completed before Blender loads/reloads and packs their pixels.
textures = (ROOT / 'tools/p08/golden/apex_textures.py').read_text(encoding='utf8')
textures = textures.replace("Art/P08/Golden/Apex'", "Art/P08/Golden/Apex/V8'")
textures = textures.replace("(.81, .83, .82), .30, .24", "(.76, .78, .79), .18, .25")
textures = textures.replace("(.045, .054, .064), .68, .34", "(.045, .048, .052), .38, .38")
textures = textures.replace("(.46, .49, .52), .94, .27", "(.44, .46, .48), .94, .29")
textures = textures.replace("(.027, .031, .036), .0, .67", "(.014, .016, .018), .0, .66")
textures = textures.replace("(.075, .105, .135), .15, .13", "(.035, .039, .045), .08, .12")
textures = textures.replace("    'Apex_RedLamp':", "    'Apex_Lens': (512, (.93, .95, .97), .0, .045, 'glass'),\n    'Apex_RedLamp':")
(ROOT / 'tools/p08/golden/apex_v8_textures.py').write_text(textures, encoding='utf8')
print('Prepared explicit V8 model and texture recipes; no Blender action yet.')
