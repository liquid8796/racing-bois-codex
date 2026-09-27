"""Fresh05: stable bounded column heights and smaller bed-to-bed offsets."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'author_beds04.py').read_text()
s=s.replace("SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_03.blend'", "SOURCE=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_04.blend'")
s=s.replace("DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_04.blend'", "DESTINATION=ROOT+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_05.blend'")
s=s.replace('Load owned frozen V19-03 separately','Load owned frozen V19-04 separately')
start=s.index('    joint_sets=[]');end=s.index('    surface_records.append(',start)
s=s[:start]+'''    intervals=[4.5+4.5*random_unit(j,seed) for j in range(joint_count)]
    factor=perimeter/sum(intervals);reference_joints=[0.0]
    for interval in intervals:reference_joints.append(reference_joints[-1]+interval*factor)
    joint_sets=[]
    for band in range(len(boundaries)+1):
        positions=[0.0]
        for joint in range(1,joint_count):
            left=reference_joints[joint]-reference_joints[joint-1]
            right=reference_joints[joint+1]-reference_joints[joint]
            shift=.16*min(left,right)*math.sin(band*1.71+joint*2.13+seed)
            positions.append(reference_joints[joint]+shift)
        positions.append(perimeter)
        if any(positions[i+1]<=positions[i] for i in range(joint_count)):
            raise RuntimeError('Joint ordering must remain strictly increasing.')
        joint_sets.append(positions)
    # Height profiles are attached to column identity, not to each row's
    # staggered XY coordinate. Analytically dz/dnominal_z >=
    # 1 - .08*(1.5/.55) - .025*pi > .70 for the bounded terms below.
    column_profiles=[]
    for joint in range(joint_count):
        interval=reference_joints[joint+1]-reference_joints[joint]
        for fraction in [0,.15,.5,.85]:
            u=reference_joints[joint]+interval*fraction
            low=0;high=lookup_count
            while high-low>1:
                middle=(low+high)//2
                if arc[middle]<=u:low=middle
                else:high=middle
            blend=(u-arc[low])/(arc[high]-arc[low]);p=plan_points[low].lerp(plan_points[high],blend)
            broad=noise.noise(Vector((p.x*.035+seed,p.y*.035-seed,seed*.37)))
            top_break=4.3*broad+2.3*noise.noise(Vector((p.x*.12,p.y*.12,seed)))
            bound=min(4.5,height*.08)
            top_break=max(-bound,min(bound,top_break))
            bed_bend=min(1.0,height*.025)*math.sin(u*.055+seed)
            column_profiles.append((top_break,bed_bend))
'''+s[end:]
s=s.replace("'bedHeightsMetres':boundaries,'rockStartMetres':rock_start,", "'bedHeightsMetres':boundaries,'rockStartMetres':rock_start,\n        'heightProfile':'Stable per-column bounded profile; analytical vertical derivative lower bound greater than0.70.',")
s=s.replace("medium=noise.noise(Vector((p.x*.11,p.y*.11,seed+band*.53)))", "medium=noise.noise(Vector((p.x*.11,p.y*.11,seed+nominal_z*.09)))")
old='''                # Bedding tilts and terminates locally; the top is not a ring
                # copied uniformly around every neighbouring butte.
                top_break=4.3*broad+2.3*noise.noise(Vector((p.x*.12,p.y*.12,seed)))
                z=nominal_z+top_break*smooth(.45,1,t)+1.0*math.sin(u*.055+seed)*math.sin(t*math.pi)'''
new='''                # Stable bounded height profile is independent of row XY
                # staggering, fixing the demonstrated04 ring inversion.
                top_break,bed_bend=column_profiles[joint*4+subdivision]
                z=nominal_z+top_break*smooth(.45,1,t)+bed_bend*math.sin(t*math.pi)'''
assert old in s;s=s.replace(old,new)
s=s.replace('(1.8+2.7*random_unit(bed+35,seed))','(.9+1.6*random_unit(bed+35,seed))')
s=s.replace('(1.5+1.8*random_unit(joint+7,seed+band))','(.65+1.15*random_unit(joint+7,seed+band))')
s=s.replace("(random_unit(joint+21,seed+band*1.67)-.5)*2.1", "(random_unit(joint+21,seed+band*1.67)-.5)*.65")
s=s.replace('''                point=Vector(center)+along*px+n*py;point.z=z
                ring.append(len(points));points.append(point)''','''                point=Vector(center)+along*px+n*py;point.z=z
                if rings and point.z<=points[rings[-1][joint*4+subdivision]].z:
                    raise RuntimeError('Authored vertical ring must strictly increase.')
                ring.append(len(points));points.append(point)''')
s=s.replace('BrokenBeds_V19_04','StableBeds_V19_05')
s=s.replace('candidate04-gameplay','candidate05-gameplay').replace('CANYON_V19_BEDS04','CANYON_V19_STABLE05')
s=s.replace("scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_03.blend'", "scene['v19_parent_source']='ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_04.blend'")
s=s.replace('Unaccepted Far33-44 broken horizontal beds, staggered rock groups and interrupted talus','Unaccepted Far33-44 stable monotonic bed strips with bounded staggering and reduced facet steps')
target=HERE/'author_stable05.py'
if target.exists():raise SystemExit('Fresh05 script required.')
target.write_text(s,newline='\n')
render=(HERE/'render_candidate04.py').read_text().replace('V19_04','V19_05').replace('candidate04','candidate05').replace('RENDER04','RENDER05')
(HERE/'render_candidate05.py').write_text(render,newline='\n')
