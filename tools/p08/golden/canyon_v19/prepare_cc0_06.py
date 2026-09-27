"""Fresh06: bounded actual CC0 relief/UVs on split rock groups; no source stretching."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
data=json.loads(Path('docs/p08/golden/canyon/v19/candidate06-cc0-patches.json').read_text())
s=(HERE/'author_stable05.py').read_text()
s=s.replace("SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_04.blend'", "SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_05.blend'")
s=s.replace("DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_05.blend'", "DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_06.blend'")
s=s.replace('Load owned frozen V19-04 separately','Load owned frozen V19-05 separately')
s=s.replace("material=bpy.data.materials['Canyon_Sandstone']", "material=bpy.data.materials['Canyon_Cliff01']\ncap_material=bpy.data.materials['Canyon_Sandstone']")
insert=s.index('def append_butte(')
helper='CC0_PATCHES='+repr(data['patches'])+'''

def reflected(value,length):
    phase=value%(length*2)
    return phase if phase<=length else length*2-phase

def sample_cc0(u,z,seed):
    patch=CC0_PATCHES[int(round(seed*100))%len(CC0_PATCHES)]
    scale=2.25+.5*random_unit(91,seed)
    x=reflected(u/scale+seed*.137,patch['widthMetres'])/patch['widthMetres']*(patch['width']-1)
    y=reflected(z/scale+seed*.219,patch['heightMetres'])/patch['heightMetres']*(patch['height']-1)
    ix=min(patch['width']-2,int(x));iy=min(patch['height']-2,int(y));tx=x-ix;ty=y-iy
    a=patch['samples'][iy][ix];b=patch['samples'][iy][ix+1]
    c=patch['samples'][iy+1][ix];d=patch['samples'][iy+1][ix+1]
    result=[]
    for k in range(3):result.append((a[k]*(1-tx)+b[k]*tx)*(1-ty)+(c[k]*(1-tx)+d[k]*tx)*ty)
    # The source front points toward-Y. Relief is applied only radially, so
    # this detail cannot change the proven vertical column ordering.
    return -result[0]*scale,(result[1],result[2])

'''
s=s[:insert]+helper+s[insert:]
s=s.replace('append_butte(points,faces,','append_butte(points,faces,point_uvs,cap_centers,')
s=s.replace('    row_z=sorted(set(row_z))','''    row_z=sorted(set(row_z))
    detail_rows=[]
    for lo,hi in zip(row_z,row_z[1:]):
        if lo>=rock_start and hi-lo>3.0:detail_rows.append((lo+hi)*.5)
    row_z=sorted(set(row_z+detail_rows))''')
s=s.replace("'heightProfile':'Stable per-column bounded profile; analytical vertical derivative lower bound greater than0.70.',", "'heightProfile':'Stable per-column bounded profile; analytical vertical derivative lower bound greater than0.70.',\n        'cc0Patch':int(round(seed*100))%len(CC0_PATCHES),'uniformDetailScale':2.25+.5*random_unit(91,seed),")
s=s.replace('active=smooth(-.42,.10,termination)','active=smooth(-.12,.22,termination)')
s=s.replace('(.65+1.15*random_unit(joint+7,seed+band))','(.18+.32*random_unit(joint+7,seed+band))')
s=s.replace('                relief+=(block-crack)*cliff_weight-terrace','''                cc0_relief,cc0_uv=sample_cc0(u,z,seed)
                relief+=(block-crack+cc0_relief)*cliff_weight-terrace''')
s=s.replace('                ring.append(len(points));points.append(point)','                ring.append(len(points));points.append(point);point_uvs.append(cc0_uv)')
s=s.replace('    bottom_center=len(points);points.append(Vector((center[0],center[1],bottom)))','    bottom_center=len(points);points.append(Vector((center[0],center[1],bottom)));point_uvs.append((0,0));cap_centers.add(bottom_center)')
s=s.replace('    top_center=len(points);points.append(Vector((center[0],center[1],top-.25)))','    top_center=len(points);points.append(Vector((center[0],center[1],top-.25)));point_uvs.append((0,0));cap_centers.add(top_center)')
s=s.replace('    points=[];faces=[]','    points=[];faces=[];point_uvs=[];cap_centers=set();record_start=len(surface_records)')
old='''    append_butte(points,faces,point_uvs,cap_centers,base_center,length*.69,82 if index<=37 else 75,min(bottom,-82),nominal-34,
                 angle+.12*math.sin(seed),0,0,seed,'base')'''
new='''    for base_group in range(2):
        center=base_center+along*((base_group-.5)*length*.48)+n*((base_group-.5)*13)
        summit=nominal-36-base_group*4+2*math.sin(seed+base_group)
        append_butte(points,faces,point_uvs,cap_centers,center,length*.39,75 if index<=37 else 68,min(bottom,-82),summit,
                     angle+.18*math.sin(seed+base_group),0,0,seed+base_group*.93,'base')'''
assert old in s;s=s.replace(old,new)
s=s.replace('    inverse=obj.matrix_world.inverted()','    for record in surface_records[record_start:]:record["moduleIndex"]=index\n    inverse=obj.matrix_world.inverted()')
old='''    mesh.from_pydata([inverse@point for point in points],[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh)'''
new='''    mesh.from_pydata([inverse@point for point in points],[],faces);mesh.update()
    mesh.materials.append(material);mesh.materials.append(cap_material)
    layer=mesh.uv_layers.new(name='UV0_CC0Surface')
    for polygon in mesh.polygons:
        polygon.material_index=1 if any(i in cap_centers for i in polygon.vertices) else 0
        for loop in polygon.loop_indices:layer.data[loop].uv=point_uvs[mesh.loops[loop].vertex_index]
    bm=bmesh.new();bm.from_mesh(mesh)'''
assert old in s;s=s.replace(old,new)
s=s.replace('bm.to_mesh(mesh);bm.free();mesh.update();mesh.materials.append(material)','bm.to_mesh(mesh);bm.free();mesh.update()')
s=s.replace('''        for index,point in zip(polygon.loop_indices,points):
            layer.data[index].uv=''','''        for index,point in zip(polygon.loop_indices,points):
            if polygon.material_index==0:continue
            layer.data[index].uv=''')
s=s.replace("'uvPolicy':'Physical world projection per triangle at2.4m/repeat; no epsilon UV offsets.'", "'uvPolicy':'Side UVs sampled from continuous originalCC0 islands; caps use physical2.4m projection. No epsilon UV offsets.'")
s=s.replace('StableBeds_V19_05','CC0BrokenGroups_V19_06')
s=s.replace('candidate05-gameplay','candidate06-gameplay').replace('CANYON_V19_STABLE05','CANYON_V19_CC006')
s=s.replace("scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_04.blend'", "scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_05.blend'")
s=s.replace('Unaccepted Far33-44 stable monotonic bed strips with bounded staggering and reduced facet steps','Unaccepted Far33-44 controlled-scale localCC0 relief and originalUVs on split bounded rock groups')
target=HERE/'author_cc0_06.py'
if target.exists():raise SystemExit('Fresh06 script required.')
target.write_text(s,newline='\n')
render=(HERE/'render_candidate05_saved.py').read_text().replace('V19_05','V19_06').replace('candidate05','candidate06').replace('RENDER05','RENDER06')
(HERE/'render_candidate06.py').write_text(render,newline='\n')
