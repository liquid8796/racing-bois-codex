"""Prepare an isolated surfacing experiment; never replaces the production bike."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
source = (ROOT / 'tools/p08/golden/apex_model_v6.py').read_text(encoding='utf-8')
source = source.replace('/Apex/V6/', '/Apex/V7/').replace('/apex/v6/', '/apex/v7/').replace('RB_Golden_Apex_v6', 'RB_Golden_Apex_v7')
source = source.replace(
    ",'Apex_Carbon','Apex_Leather'", '')
source = source.replace("scene.cycles.samples = 32", "scene.cycles.samples = 24")
start = source.index('def ring_panel(')
end = source.index('\ndef torus(', start)
source = source[:start] + '''def ring_panel(name,outer,inner,side,width,material):
    # Four quad bands replace the single low-density fan which previously
    # buckled into planar triangles. A physical edge return defines thickness.
    boundary_steps=4; bands=6
    sampled=[]
    for profile in [outer,inner]:
        boundary=[]
        for i in range(len(profile)):
            a=profile[i];b=profile[(i+1)%len(profile)]
            for j in range(boundary_steps):
                t=j/boundary_steps
                boundary.append((a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t))
        sampled.append(boundary)
    n=len(sampled[0]); vertices=[]; faces=[]; uv=[]
    def surface(y,z,t):
        # Deliberate rolled shoulder taper: body wraps down to narrow sump,
        # curves toward the nose, and turns inward at the vent perimeter.
        lower_taper=max(0,.68-y)*.32
        rear_taper=max(0,.12-z)*.16
        nose_taper=max(0,z-.66)*.17
        roll=.037*math.sin(t*math.pi)
        return side*(width-lower_taper-rear_taper-nose_taper+roll)
    for k in range(bands+1):
        t=k/bands
        for i in range(n):
            a=sampled[0][i];b=sampled[1][i]
            y=a[0]*(1-t)+b[0]*t;z=a[1]*(1-t)+b[1]*t
            vertices.append((surface(y,z,t),y,z));uv.append((z*1.7,y*1.7))
            if k:
                j=(i+1)%n;faces.append(((k-1)*n+i,(k-1)*n+j,k*n+j,k*n+i))
    # The inner wall ends in the air duct; the outer edge turns in 12 mm.
    for band in [0,bands]:
        begin=len(vertices)
        for i in range(n):
            x,y,z=vertices[band*n+i]
            vertices.append((x-side*.012,y,z));uv.append((z*1.7,y*1.7))
        for i in range(n):
            j=(i+1)%n
            faces.append((band*n+i,band*n+j,begin+j,begin+i))
    return mesh(name,vertices,faces,material,uv=uv,smooth=True)

def sculpted_tank():
    # Faceted shoulder, broad crown, pinched knee scallop. The prior all-round
    # superellipse could only produce a balloon and is not used for this part.
    sections=[(-.205,.846,.070,.805),(-.155,.884,.112,.794),
              (-.070,.970,.166,.788),(.040,1.032,.205,.789),
              (.180,1.053,.220,.795),(.290,1.027,.201,.806),
              (.380,.935,.143,.818),(.425,.870,.066,.832)]
    cross=[(0,1),(.55,.985),(.84,.87),(1,.61),(.91,.30),
           (.60,.03),(0,0),(-.60,.03),(-.91,.30),(-1,.61),(-.84,.87),(-.55,.985)]
    vertices=[];faces=[];uv=[]
    for k,(z,top,width,bottom) in enumerate(sections):
        for j,(xx,yy) in enumerate(cross):
            vertices.append((xx*width,bottom+(top-bottom)*yy,z))
            uv.append((j/len(cross),(z+.22)/.65))
            if k:
                n=len(cross);q=(j+1)%n
                faces.append(((k-1)*n+j,(k-1)*n+q,k*n+q,k*n+j))
    n=len(cross)
    faces.extend([tuple(reversed(range(n))),tuple((len(sections)-1)*n+j for j in range(n))])
    return mesh('Apex tailored tank shoulders',vertices,faces,'Apex_Pearl',bevel=.006,uv=uv)
''' + source[end:]
start=source.index("loft('Apex sculpted tank'")
end=source.index('\n',start)
source=source[:start]+'sculpted_tank()'+source[end:]
source=source.replace("(0,1.087,.14),(0,1.094,.14)","(0,1.053,.17),(0,1.059,.17)")
source=source.replace("(0,1.091,.14),(0,1.099,.14)","(0,1.057,.17),(0,1.062,.17)")
source=source.replace("(0,1.100,.14)","(0,1.063,.17)")
source=source.replace(
    'outer=[(.984,.50),(.940,.73),(.826,.79),(.590,.64),(.310,.53),(.350,.30),(.570,-.17),(.735,-.14)]',
    'outer=[(.986,.55),(.952,.80),(.836,.963),(.596,.67),(.266,.505),(.373,.255),(.559,-.158),(.773,-.104)]')
source=source.replace("ring_panel('Eight edge upper fairing',outer,inner,side,.235", "ring_panel('Sculpted continuous side fairing',outer,inner,side,.247")
# Old front cheek is a disconnected n-gon. Return toward the side fairing with
# an actual fitted overlap, and use quads instead of one nonplanar polygon.
source=source.replace("(side*.261,.954,.64)","(side*.251,.974,.55)")
source=source.replace("'Apex_Pearl',bevel=.004,smooth=False)","'Apex_Pearl',bevel=.003,smooth=True)")
source=source.replace("'Carbon lower belly pan'", "'Shaped lower belly pan'")
# Do not create LODs/export a failed shape experiment. Keep all editable parts
# visible for inspection and save the candidate source and fixed review image.
start=source.index("# Contacts/markers are separate")
lighting=source.index("# Neutral studio lighting.",start)
source=source[:start]+'''# Candidate surfacing experiment; components remain editable. No FBX or
# production descriptor is issued before independent visual review.
for obj in parts+wheel_parts['Front']+wheel_parts['Rear']:
    world=obj.matrix_world.copy();obj.parent=root;obj.matrix_world=world
''' + source[lighting:]
start=source.index('\ncounts=[]')
source=source[:start]+'''
print('APEX_V7_CANDIDATE_SAVED '+SOURCE+NAME+'.blend')
'''
for relative in ['ArtSource/P08/Golden/Apex/V7','Assets/RacingBois/Art/P08/Golden/Apex/V7','docs/p08/golden/apex/v7']:
    (ROOT/relative).mkdir(parents=True,exist_ok=True)
for path in (ROOT/'Assets/RacingBois/Art/P08/Golden/Apex').glob('*.png'):
    shutil.copy2(path, ROOT/'Assets/RacingBois/Art/P08/Golden/Apex/V7'/path.name)
destination=ROOT/'tools/p08/golden/apex_model_v7.py'
destination.write_text(source,encoding='utf-8')
compile(source,str(destination),'exec')
print(destination)
