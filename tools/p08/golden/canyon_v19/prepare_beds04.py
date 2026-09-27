"""Derive a fresh self-contained04 study from preserved03 audit scaffolding."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=(HERE/'author_fractures03.py').read_text()
source=source.replace("SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_02.blend'", "SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_03.blend'")
source=source.replace("DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_03.blend'", "DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_04.blend'")
source=source.replace('Load owned frozen V19-02 separately','Load owned frozen V19-03 separately')
start=source.index('def append_butte(');end=source.index('def build_terraced_mass(',start)
source=source[:start]+'''def append_butte(points,faces,center,rx,ry,bottom,top,angle,segments,vertical,seed,kind):
    n=Vector((math.cos(angle),math.sin(angle),0));along=Vector((-n.y,n.x,0))
    # A dense temporary plan lookup does not add mesh vertices. Mesh vertices
    # occur at fracture valleys/shoulders and explicit bed transitions only.
    lookup_count=2048;plan_points=[plan(2*math.pi*i/lookup_count,rx,ry) for i in range(lookup_count+1)]
    arc=[0.0]
    for i in range(lookup_count):arc.append(arc[-1]+(plan_points[i+1]-plan_points[i]).length)
    perimeter=arc[-1];joint_count=max(12,round(perimeter/7.0))
    height=top-bottom
    rock_start=max(bottom,-13+7*math.sin(seed)) if kind=='base' else bottom
    boundaries=[];level=rock_start+6.0+3*random_unit(6,seed)
    while level<top-3:
        boundaries.append(level);level+=6.0+5*random_unit(len(boundaries)+12,seed)
    row_z=[bottom,top]
    if rock_start>bottom+2:
        row_z.extend([bottom+(rock_start-bottom)*.32,bottom+(rock_start-bottom)*.67,rock_start])
    for boundary in boundaries:row_z.extend([boundary-.9,boundary+.9])
    row_z=sorted(set(row_z))
    joint_sets=[]
    for band in range(len(boundaries)+1):
        intervals=[4.5+4.5*random_unit(j,seed+band*1.67) for j in range(joint_count)]
        factor=perimeter/sum(intervals);positions=[0.0]
        for interval in intervals:positions.append(positions[-1]+interval*factor)
        joint_sets.append(positions)
    surface_records.append({'seed':seed,'kind':kind,'referencePlanPerimeterMetres':perimeter,
        'jointsPerBed':joint_count,'verticesPerRing':joint_count*4,'verticalRings':len(row_z),
        'bedHeightsMetres':boundaries,'rockStartMetres':rock_start,
        'sampling':'Vertices at fractured block shoulders and bed transitions; no uniform dense grid.'})
    rings=[]
    for row,nominal_z in enumerate(row_z):
        t=(nominal_z-bottom)/height;ring=[]
        band=0
        while band<len(boundaries) and nominal_z>boundaries[band]:band+=1
        positions=joint_sets[band]
        for joint in range(joint_count):
            interval=positions[joint+1]-positions[joint]
            for subdivision,fraction in enumerate([0,.15,.5,.85]):
                u=positions[joint]+interval*fraction
                low=0;high=lookup_count
                while high-low>1:
                    middle=(low+high)//2
                    if arc[middle]<=u:low=middle
                    else:high=middle
                blend=(u-arc[low])/(arc[high]-arc[low])
                p=plan_points[low].lerp(plan_points[high],blend)
                theta=2*math.pi*(low+blend)/lookup_count
                broad=noise.noise(Vector((p.x*.035+seed,p.y*.035-seed,seed*.37)))
                medium=noise.noise(Vector((p.x*.11,p.y*.11,seed+band*.53)))
                # Bedding tilts and terminates locally; the top is not a ring
                # copied uniformly around every neighbouring butte.
                top_break=4.3*broad+2.3*noise.noise(Vector((p.x*.12,p.y*.12,seed)))
                z=nominal_z+top_break*smooth(.45,1,t)+1.0*math.sin(u*.055+seed)*math.sin(t*math.pi)
                radial=p.normalized()
                if kind=='base':
                    talus_end=rock_start+8*math.sin(theta*2.7+seed)
                    foot=max(0,(talus_end-z)/max(1,talus_end-bottom))
                    lobe=.30+.70*max(0,math.sin(theta*3+seed))**2
                    outward=76*lobe*foot**1.25
                    scale=.77;cliff_weight=smooth(rock_start-4,rock_start+8,z)
                    relief=3.5*noise.noise(Vector((p.x*.045,p.y*.045,z*.05+seed)))
                    relief+=2.0*noise.noise(Vector((p.x*.12,p.y*.12,z*.15+seed)))
                else:
                    outward=7*(1-t)**1.4 if kind=='spur' else 0.0
                    scale=1-.035*t;cliff_weight=1.0
                    relief=2.3*broad+1.15*medium
                terrace=0.0
                for bed,boundary in enumerate(boundaries):
                    termination=noise.noise(Vector((u*.022+bed*2.1,seed,bed*.73)))
                    active=smooth(-.42,.10,termination)
                    terrace+=(1.8+2.7*random_unit(bed+35,seed))*active*smooth(boundary-.9,boundary+.9,nominal_z)
                # Joints change position in every bed. A finite valley joins
                # neighbouring angular block faces, rather than a continuous
                # sinusoidal rib repeated from foundation to summit.
                crack=(1.5+1.8*random_unit(joint+7,seed+band)) if subdivision==0 else 0.0
                block=(random_unit(joint+21,seed+band*1.67)-.5)*2.1
                relief+=(block-crack)*cliff_weight-terrace
                relief=max(relief,-p.length*.55)
                px=p.x*scale+radial.x*(outward+relief)
                py=p.y*scale+radial.y*(outward+relief)
                point=Vector(center)+along*px+n*py;point.z=z
                ring.append(len(points));points.append(point)
        rings.append(ring)
    count=joint_count*4
    for row in range(len(rings)-1):
        for column in range(count):
            nxt=(column+1)%count
            faces.append((rings[row][column],rings[row][nxt],rings[row+1][nxt],rings[row+1][column]))
    bottom_center=len(points);points.append(Vector((center[0],center[1],bottom)))
    top_center=len(points);points.append(Vector((center[0],center[1],top-.25)))
    for column in range(count):
        nxt=(column+1)%count
        faces.append((bottom_center,rings[0][nxt],rings[0][column]))
        faces.append((top_center,rings[-1][column],rings[-1][nxt]))

surface_records=[]

'''+source[end:]
start=source.index('    segments=640');end=source.index('    inverse=obj.matrix_world.inverted()',start)
source=source[:start]+'''    base_center=anchor-n*24
    append_butte(points,faces,base_center,length*.69,82 if index<=37 else 75,min(bottom,-82),nominal-34,
                 angle+.12*math.sin(seed),0,0,seed,'base')
    count=2+(index%3)
    for group in range(count):
        fraction=(group+.5)/count-.5
        offset=fraction*.78*length
        summit=nominal-3-11*random_unit(group+1,seed)
        rx=length*(.27 if count==2 else .22 if count==3 else .17)
        ry=26+7*random_unit(group+3,seed)
        center=anchor+along*offset-n*(19+24*random_unit(group+8,seed))
        append_butte(points,faces,center,rx,ry,nominal-45,summit,
                     angle+.38*(random_unit(group+12,seed)-.5),0,0,seed+2.1+group*2.7,'upper')
    for group in range(2+(index%2)):
        offset=(group-.6)*length*.22
        center=base_center+n*(54+5*math.sin(seed+group))+along*offset
        append_butte(points,faces,center,14+6*random_unit(group+19,seed),13+4*random_unit(group+20,seed),
                     -39,nominal-50-8*random_unit(group+29,seed),angle+.35*math.sin(seed+group),0,0,seed+9.3+group,'spur')
'''+source[end:]
source=source.replace('PhysicalFractures_V19_03','BrokenBeds_V19_04')
source=source.replace('candidate03-gameplay','candidate04-gameplay').replace('CANYON_V19_FRACTURES03','CANYON_V19_BEDS04')
source=source.replace('Unaccepted Far33-44 fractured closed mesas and sloping talus','Unaccepted Far33-44 broken horizontal beds, staggered rock groups and interrupted talus')
source=source.replace("scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_02.blend'", "scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_03.blend'")
target=HERE/'author_beds04.py'
if target.exists():raise SystemExit('Fresh04 script required.')
target.write_text(source,newline='\n')
render=(HERE/'render_candidate03.py').read_text().replace('V19_03','V19_04').replace('candidate03','candidate04').replace('RENDER03','RENDER04')
(HERE/'render_candidate04.py').write_text(render,newline='\n')
