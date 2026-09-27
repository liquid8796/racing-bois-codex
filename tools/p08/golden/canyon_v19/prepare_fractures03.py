"""Prepare a fresh, self-contained candidate script without modifying frozen02."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
original = (HERE / 'author_mesas02.py').read_text(encoding='utf-8')
candidate = original.replace('V19_02.blend', 'V19_03.blend').replace('candidate02-gameplay', 'candidate03-gameplay')
candidate = candidate.replace("SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V18/RB_Golden_Canyon_V18_02.blend'", "SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_02.blend'")
candidate = candidate.replace('Load owned frozen V18-02 separately', 'Load owned frozen V19-02 separately')
start = candidate.index('def append_butte(')
end = candidate.index('def build_terraced_mass(', start)
candidate = candidate[:start] + '''def random_unit(index,seed):
    value=math.sin(index*127.1+seed*311.7)*43758.5453
    return value-math.floor(value)

def plan(theta,rx,ry):
    c,s=math.cos(theta),math.sin(theta)
    return Vector(((1 if c>=0 else -1)*abs(c)**.82*rx,
                   (1 if s>=0 else -1)*abs(s)**.82*ry,0))

def append_butte(points,faces,center,rx,ry,bottom,top,angle,segments,vertical,seed,kind):
    n=Vector((math.cos(angle),math.sin(angle),0));along=Vector((-n.y,n.x,0))
    # Physical arc-length coordinates avoid a fixed small joint count around
    # huge masses. Each joint interval is explicitly 3 to 10 metres.
    arc=[0.0];previous=plan(0,rx,ry)
    for column in range(1,segments+1):
        point=plan(2*math.pi*column/segments,rx,ry)
        arc.append(arc[-1]+(point-previous).length);previous=point
    perimeter=arc[-1]
    joints=[0.0];joint_index=0
    while joints[-1]<perimeter:
        joints.append(joints[-1]+4+5*random_unit(joint_index,seed));joint_index+=1
    # Redistribute only the final short remainder by uniform scaling. Record
    # the actual resulting spacings instead of claiming an idealised range.
    factor=perimeter/joints[-1];joints=[value*factor for value in joints]
    spacing=[joints[i+1]-joints[i] for i in range(len(joints)-1)]
    surface_records.append({'seed':seed,'kind':kind,'perimeterMetres':perimeter,
        'jointCount':len(spacing),'minimumJointSpacingMetres':min(spacing),
        'maximumJointSpacingMetres':max(spacing),'angularSegments':segments,
        'maximumSurfaceArcStepMetres':max(arc[i+1]-arc[i] for i in range(segments))})
    rings=[]
    for row in range(vertical+1):
        t=row/vertical;ring=[]
        for column in range(segments):
            theta=2*math.pi*column/segments;u=arc[column]
            p=plan(theta,rx,ry);c,s=math.cos(theta),math.sin(theta)
            # Several nonperiodic scales shape the skyline and large setbacks.
            broad=noise.noise(Vector((p.x*.028+seed,p.y*.028-seed,seed*.37)))
            medium=noise.noise(Vector((p.x*.09,p.y*.09,seed)))
            highest=top+5.8*broad+2.7*medium+1.4*math.sin(theta*3.1+seed)
            z=bottom+(highest-bottom)*t
            if kind=='base':
                # Continuous sloping talus below the upper ledge. This replaces
                # the prior tall, nearly vertical blank cylinder.
                scale=.73
                outward=108*(1-t)**1.35
                cliff_weight=smooth(.72,.94,t)
            elif kind=='spur':
                scale=.79-.08*smooth(.68,.77,t)
                outward=44*(1-t)**1.3
                cliff_weight=.3+.7*smooth(.5,.8,t)
            else:
                scale=1-.10*t-.07*smooth(.28,.36,t)-.09*smooth(.68,.75,t)
                outward=0.0;cliff_weight=1.0
            # Deep, irregular 15–35m setbacks coexist with physically smaller
            # rock faces. Relief is metre-scale geometry, not a texture claim.
            radial=Vector((p.x,p.y,0)).normalized()
            relief=4.2*broad+2.7*medium
            warped=(u+.45*math.sin(z*.23+seed)+.65*noise.noise(Vector((u*.08,z*.1,seed))))%perimeter
            joint=0
            while joint+1<len(joints)-1 and joints[joint+1]<warped:joint+=1
            left=warped-joints[joint];right=joints[joint+1]-warped
            distance=min(left,right)
            depth=1.7+2.3*random_unit(joint+17,seed)
            width=.58+.68*random_unit(joint+39,seed)
            # Tapered V cuts have sloped sidewalls and remain visible at the
            # comparison distance. Broken joints terminate at varying beds.
            activity=.45+.55*smooth(.02,.24,t)
            crack=depth*max(0,1-distance/width)*activity
            bed_spacing=4.8+2.8*random_unit(8,seed)
            phase=z+1.6*noise.noise(Vector((u*.045,seed,0)))+.8*math.sin(u*.07+seed)
            bed_distance=abs((phase+1000)%bed_spacing-bed_spacing*.5)
            bedding=(1.15+.75*medium)*max(0,1-bed_distance/1.15)
            fine=.9*noise.noise(Vector((p.x*.38,p.y*.38,z*.41+seed)))
            relief+=(fine-crack-bedding)*cliff_weight
            px=p.x*scale+radial.x*(outward+relief)
            py=p.y*scale+radial.y*(outward+relief)
            point=Vector(center)+along*px+n*py;point.z=z
            ring.append(len(points));points.append(point)
        rings.append(ring)
    for row in range(vertical):
        for column in range(segments):
            nxt=(column+1)%segments
            faces.append((rings[row][column],rings[row][nxt],rings[row+1][nxt],rings[row+1][column]))
    bottom_center=len(points);points.append(Vector((center[0],center[1],bottom)))
    top_center=len(points);points.append(Vector((center[0],center[1],top-.25)))
    for column in range(segments):
        nxt=(column+1)%segments
        faces.append((bottom_center,rings[0][nxt],rings[0][column]))
        faces.append((top_center,rings[-1][column],rings[-1][nxt]))

surface_records=[]

''' + candidate[end:]
candidate = candidate.replace('segments=64 if index<=36 else 48\n    levels=26 if index<=36 else 20', 'segments=640 if index<=36 else 448\n    levels=90 if index<=36 else 72')
candidate = candidate.replace('min(bottom,-82),nominal-31', 'min(bottom,-82),nominal-36')
candidate = candidate.replace("[(-.21,0,35,2.1),(.22,-10,29,4.3)]", "[(-.21,0,41,2.1),(.22,10,38,4.3)]")
candidate = candidate.replace("angle+.18*math.sin(seed+phase),segments,levels,seed+phase,'upper'", "angle+.18*math.sin(seed+phase),384 if index<=36 else 256,48 if index<=36 else 40,seed+phase,'upper'")
candidate = candidate.replace("angle-.21*math.sin(seed),segments,levels,seed+6.7,'spur'", "angle-.21*math.sin(seed),384 if index<=36 else 256,levels,seed+6.7,'spur'")
candidate = candidate.replace('Canyon_Far%02d_FullPerimeterMesas_V19_L0', 'Canyon_Far%02d_PhysicalFractures_V19_03_L0')
candidate = candidate.replace('CANYON_V19_MESAS02', 'CANYON_V19_FRACTURES03')
candidate = candidate.replace("'layout':layout,'audit':rows", "'layout':layout,'physicalSurfaces':surface_records,'audit':rows")
candidate = candidate.replace('Unaccepted Far33-44 full-perimeter sculpted closed mesas', 'Unaccepted Far33-44 fractured closed mesas and sloping talus')
candidate = candidate.replace("scene['v19_parent_source_sha256']='08ac16ebb9467dbe2db922fb9aa84ff49998134f830049cd9ca5caf767ad3e78'", "scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_02.blend'")
destination = HERE / 'author_fractures03.py'
if destination.exists():
    raise SystemExit('Fresh candidate script required.')
destination.write_text(candidate, encoding='utf-8', newline='\n')
render=(HERE/'render_candidate02.py').read_text(encoding='utf-8').replace('V19_02','V19_03').replace('candidate02','candidate03').replace('RENDER02','RENDER03')
(HERE/'render_candidate03.py').write_text(render, encoding='utf-8', newline='\n')
