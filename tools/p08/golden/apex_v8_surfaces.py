"""Bespoke body skins. Appended after V8's geometry/material helpers."""

def cubic_samples(points, steps=4, closed=False):
    samples=[]
    for i in range(len(points) if closed else len(points)-1):
        p0=Vector(points[(i-1)%len(points)] if closed else points[max(0,i-1)])
        p1=Vector(points[i]);p2=Vector(points[(i+1)%len(points)])
        p3=Vector(points[(i+2)%len(points)] if closed else points[min(len(points)-1,i+2)])
        for step in range(steps):
            t=step/steps
            samples.append((2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)*.5)
    if not closed:samples.append(Vector(points[-1]))
    return samples

def tailored_volume(name,sections,profile,material,steps=4):
    rings=cubic_samples(sections,steps)
    cross=cubic_samples(profile,3,True)
    vertices=[];faces=[];uv=[];n=len(cross)
    for k,section in enumerate(rings):
        z,bottom,top,width=section
        for j,p in enumerate(cross):
            vertices.append((p[0]*width,bottom+(top-bottom)*p[1],z))
            uv.append((j/n,(z+1.1)/2.2))
        if k:
            for j in range(n):faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    faces.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+j for j in range(n))])
    return mesh(name,vertices,faces,material,uv=uv)

def skin(name,points,faces,material,thickness=.006,bevel=.0012,smooth=True):
    obj=mesh(name,points,faces,material,smooth=smooth)
    bpy.context.view_layer.objects.active=obj
    modifier=obj.modifiers.new('Manufactured skin thickness','SOLIDIFY')
    modifier.thickness=thickness;modifier.offset=-1
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    if bevel:
        modifier=obj.modifiers.new('Subtle manufactured edge','BEVEL')
        modifier.width=bevel;modifier.segments=3;modifier.limit_method='ANGLE';modifier.angle_limit=.45
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj

def curved_patch(name,corners,material,rows=6,cols=8,bulge=0):
    # Four corner Coons strip with a very small continuous camber. Distinct
    # styling creases are separate patches, not a smoothed radial ngon fan.
    a,b,c,d=[Vector(p) for p in corners]
    vertices=[];faces=[]
    normal=(b-a).cross(d-a).normalized()
    for r in range(rows+1):
        t=r/rows
        for j in range(cols+1):
            u=j/cols
            p=a*(1-u)*(1-t)+b*u*(1-t)+c*u*t+d*(1-u)*t
            p+=normal*(bulge*math.sin(math.pi*u)*math.sin(math.pi*t))
            vertices.append(p)
            if r and j:
                k=r*(cols+1)+j;faces.append((k-cols-2,k-cols-1,k,k-1))
    return skin(name,vertices,faces,material)

# The crown and knee scallops follow distinct longitudinal curves. Ring
# density follows profile curvature; no flat tank facets or balloon loft.
tank_cross=[(0,1),(.42,.99),(.73,.91),(.96,.74),(1,.56),(.89,.31),(.63,.04),(0,0),(-.63,.04),(-.89,.31),(-1,.56),(-.96,.74),(-.73,.91),(-.42,.99)]
tailored_volume('Sculpted pearl fuel tank',[
    (-.225,.802,.875,.075),(-.17,.793,.91,.108),(-.07,.785,.990,.169),
    (.055,.789,1.027,.211),(.19,.798,1.026,.212),(.29,.805,.997,.190),
    (.365,.814,.948,.137),(.40,.831,.897,.071)],tank_cross,'Apex_Pearl',4)
tailored_volume('Tank underside knee mounting',[
    (-.235,.772,.819,.074),(-.04,.765,.824,.138),(.20,.785,.826,.17),(.39,.813,.842,.09)],
    [(0,1),(.8,1),(1,.70),(.65,0),(-.65,0),(-1,.70),(-.8,1)],'Apex_Graphite')
rod('Flush fuel cap gasket',(0,1.030,.153),(0,1.033,.153),.043,'Apex_Graphite',sides=48)
rod('Machined fuel filler',(0,1.033,.153),(0,1.035,.153),.035,'Apex_Machined',sides=48)
block('Filler release',(0,1.036,.153),(.014,.002,.028),'Apex_Graphite',.002)
for j in range(6):
    a=j*math.tau/6
    rod('Fuel cap socket screw',(.029*math.cos(a),1.035,.153+.029*math.sin(a)),(.029*math.cos(a),1.037,.153+.029*math.sin(a)),.0021,'Apex_Graphite',sides=6)

seat_cross=[(0,1),(.72,.99),(1,.70),(.92,.14),(.63,0),(-.63,0),(-.92,.14),(-1,.70),(-.72,.99)]
tailored_volume('Contoured rider saddle',[(-.620,.809,.889,.115),(-.573,.788,.854,.135),(-.47,.780,.826,.134),(-.36,.786,.826,.126),(-.25,.795,.837,.108),(-.184,.806,.857,.079)],seat_cross,'Apex_Rubber')
tailored_volume('Tapered white tail shell',[(-1.014,.962,.985,.070),(-.948,.928,.981,.105),(-.838,.858,.932,.139),(-.70,.788,.877,.148),(-.57,.761,.809,.137),(-.43,.765,.794,.121),(-.226,.777,.814,.079)],
    [(0,1),(.65,1),(.97,.88),(1,.59),(.61,.02),(0,0),(-.61,.02),(-1,.59),(-.97,.88),(-.65,1)],'Apex_Pearl')
tailored_volume('Elevated compact passenger saddle',[(-.985,.981,1.012,.063),(-.94,.979,1.014,.09),(-.86,.94,.996,.10),(-.808,.918,.979,.09)],seat_cross,'Apex_Rubber')
for side in [-1,1]:
    tube('Saddle tailored perimeter',[(side*.11,.876,-.620),(side*.134,.843,-.573),(side*.133,.819,-.47),(side*.125,.82,-.36),(side*.106,.831,-.25),(side*.078,.848,-.184)],.0018,'Apex_Graphite',sides=6)
    # Black triangular insert is recessed into the falling shoulder of tail.
    points=[(side*.110,.950,-.944),(side*.136,.885,-.826),(side*.148,.824,-.70),(side*.128,.889,-.847)]
    skin('Rear side black vent insert',points,[(0,1,2,3)],'Apex_Graphite',.002,.001,False)

def fairing_x(y,z):
    return .247-.105*((y-.80)/.63)**2-.025*max(0,z-.54)/.40-.025*max(0,.08-z)/.25

def duct_shell(side):
    # The silhouette and the actual diagonal through-opening use matched
    # boundary correspondence. X comes only from surface position, not band
    # interpolation, so smoothing cannot inflate a ring around the opening.
    outer=[(.799,.776),(.905,.580),(.825,.330),(.645,.052),(.502,.015),(.382,.208),(.195,.440),(.520,.468)]
    inner=[(.763,.447),(.785,.335),(.757,.283),(.687,.243),(.605,.172),(.589,.245),(.694,.346),(.742,.414)]
    samples=[]
    for boundary in [outer,inner]:
        p=[]
        for i in range(len(boundary)):
            a=boundary[i];b=boundary[(i+1)%len(boundary)]
            for j in range(4):
                t=j/4;p.append((a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t))
        samples.append(p)
    n=len(samples[0]);vertices=[];faces=[];uv=[]
    for k in range(7):
        t=k/6
        for j in range(n):
            a,b=samples[0][j],samples[1][j]
            y=a[0]*(1-t)+b[0]*t;z=a[1]*(1-t)+b[1]*t
            # Tight moulded return only in the last two percent of opening.
            x=fairing_x(y,z)-.003*(max(0,t-.96)/.04)
            vertices.append((side*x,y,z));uv.append((z*1.7,y*1.7))
        if k:
            for j in range(n):faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    obj=mesh('Pearl side fairing with diagonal through duct',vertices,faces,'Apex_Pearl',uv=uv)
    bpy.context.view_layer.objects.active=obj
    modifier=obj.modifiers.new('Moulded fairing skin','SOLIDIFY');modifier.thickness=.006;modifier.offset=-1
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    # Actual recessed walls and honeycomb screen, inset thirty millimetres.
    wall=[];wall_faces=[]
    for depth in [0,.034]:
        for y,z in samples[1]:wall.append((side*(fairing_x(y,z)-.004-depth),y,z))
    for j in range(n):wall_faces.append((j,(j+1)%n,n+(j+1)%n,n+j))
    skin('Intake cavity deep black wall',wall,wall_faces,'Apex_Graphite',.003,.001)
    # Narrow diamond-wire cells occupy the actual opening rather than broad
    # silver grille bars, preserving the reference's deep dark intake.
    for j in range(15):
        t=j/14;y=.611+.147*t;z=.215+.150*t
        x=side*(fairing_x(y,z)-.026)
        rod('Duct screen fine horizontal',(x,y,z-.027),(x,y,z+.028),.0008,'Apex_Machined',sides=4)
    for j in range(5):
        offset=(j-2)*.011
        rod('Duct screen diagonal',(side*.214,.611,.212+offset),(side*.214,.758,.362+offset),.0008,'Apex_Graphite',sides=4)

for side in [-1,1]:
    duct_shell(side)
    # Visible pearl/graphite boundary forms the long deliberate shoulder
    # crease descending from steering head toward the saddle front.
    curved_patch('Spar exposed graphite shoulder',[(side*.135,.937,.38),(side*.186,.88,.31),(side*.171,.759,-.155),(side*.129,.791,-.225)],'Apex_Graphite',bulge=.003)
    curved_patch('Narrow pearl shoulder return',[(side*.153,.938,.37),(side*.177,.949,.416),(side*.187,.855,.180),(side*.179,.813,.072)],'Apex_Pearl',bulge=.002)
    # Belly pan is a contoured volume, with a deliberately sharp upper chine.
    curved_patch('Belly pan outer charcoal',[(side*.165,.37,-.339),(side*.20,.364,.202),(side*.17,.194,.440),(side*.103,.236,-.332)],'Apex_Graphite',bulge=.005)
    curved_patch('Belly upper chamfer',[(side*.136,.399,-.282),(side*.185,.416,.143),(side*.20,.364,.202),(side*.165,.37,-.339)],'Apex_Graphite',bulge=.001)
    # Long lower cooling relief, visually black and set behind white skin.
    skin('Lower cooling relief black',[(side*.215,.520,.066),(side*.223,.477,.128),(side*.214,.358,.290),(side*.186,.371,.201)],[(0,1,2,3)],'Apex_Rubber',.004,.001,False)
    # Tiny flush fasteners at the real panel attachment positions.
    for y,z in [(.800,.466),(.664,.072),(.544,.066),(.301,.408)]:
        x=fairing_x(y,z)
        rod('Flush fairing socket',(side*x,y,z),(side*(x+.0023),y,z),.0055,'Apex_Machined',sides=10)
        rod('Flush fairing socket recess',(side*(x+.0024),y,z),(side*(x+.0028),y,z),.0021,'Apex_Graphite',sides=6)
tailored_volume('Closed angular sump skin',[(-.35,.224,.254,.104),(-.18,.205,.249,.154),(.16,.190,.233,.165),(.44,.183,.200,.146)],
    [(0,1),(1,.85),(1,.4),(.72,0),(-.72,0),(-1,.4),(-1,.85)],'Apex_Graphite')

# Attached windscreen with black centre nose forming one visual spine. The
# painted cheeks are individually fitted around real recessed lamp cavities.
nose_parts_start=len(parts)
for side in [-1,1]:
    points=[];faces=[]
    for r in range(13):
        t=r/12
        for j in range(17):
            q=.16+.84*j/16
            a=Vector((side*q*.209,1.033-.055*q*q,.60+.04*q*q))
            b=Vector((side*q*.225,.840+.090*q**.30,1.015-.109*q*q))
            p=a*(1-t)+b*t
            p.y+=.009*math.sin(t*math.pi)*math.sin(q*math.pi)
            points.append(p)
            if r and j:
                k=r*17+j;faces.append((k-18,k-17,k,k-1))
    skin('Continuous fitted upper nose half',points,faces,'Apex_Pearl',.006,.0015)
    curved_patch('Nose wrapped outer cheek',[(side*.209,.978,.64),(side*.225,.930,.906),(side*.222,.851,.950),(side*.245,.906,.760)],'Apex_Pearl',bulge=.002)
    curved_patch('Nose lower lamp return',[(side*.021,.813,1.022),(side*.226,.837,.970),(side*.223,.853,.952),(side*.025,.833,1.016)],'Apex_Pearl',bulge=.001)
    outline=[(side*.028,.836,1.015),(side*.038,.883,1.005),(side*.206,.920,.915),(side*.226,.873,.947),(side*.212,.849,.966)]
    center=sum((Vector(p) for p in outline),Vector())/len(outline)
    inset=[tuple(center+(Vector(p)-center)*.91) for p in outline]
    n=len(outline)
    ringpoints=outline+inset
    ringfaces=[(j,(j+1)%n,n+(j+1)%n,n+j) for j in range(n)]
    skin('Hollow headlamp perimeter gasket',ringpoints,ringfaces,'Apex_Graphite',.011,.0015,False)
    back=[(x,y,z-.033) for x,y,z in inset]
    skin('Deep lamp rear black enclosure',back,[tuple(range(n))],'Apex_Graphite',.002,.001,False)
    wall=inset+back
    skin('Recessed lamp cavity walls',wall,ringfaces,'Apex_Graphite',.002,.001,False)
    front=[(x,y,z+.0015) for x,y,z in inset]
    skin('Clear flush lamp cover',front,[tuple(range(n))],'Apex_Lens',.001,.0005,False)
    # Projectors live behind the angled lens, not on the outer paint surface.
    for index,(x,y,z,r) in enumerate([(.103,.868,.983,.021),(.173,.880,.953,.014)]):
        rod('Reflector barrel',(side*x,y,z-.025),(side*x,y,z-.004),r,'Apex_Machined',sides=32)
        rod('Projector lens',(side*x,y,z-.004),(side*x,y,z-.001),r*.61,'Apex_Lamp',sides=32)
    # The concept mirror housing is a trapezoidal shell, not an oval lozenge.
    tube('Short fairing mirror bracket',[(side*.190,.984,.57),(side*.268,1.020,.535),(side*.321,1.075,.525)],.007,'Apex_Graphite',sides=12)
    mirror_outline=[(side*.295,1.059,.543),(side*.404,1.075,.538),(side*.412,1.129,.517),(side*.326,1.133,.504)]
    skin('Angular fairing mirror case',mirror_outline,[(0,1,2,3)],'Apex_Graphite',.022,.003,False)
    mc=sum((Vector(p) for p in mirror_outline),Vector())/4
    mirror_face=[tuple(mc+(Vector(p)-mc)*.84+Vector((0,0,-.003))) for p in mirror_outline]
    skin('Inset rear facing mirror',mirror_face,[(0,1,2,3)],'Apex_Machined',.001,.0005,False)

vertices=[];faces=[]
for r in range(16):
    t=r/15
    for j in range(17):
        q=(j/8-1)*.16
        a=Vector((q*.209,1.033-.055*q*q,.60+.04*q*q))
        b=Vector((q*.225,.840+.090*abs(q)**.30,1.015-.109*q*q))
        p=a*(1-t)+b*t
        p.y+=.009*math.sin(t*math.pi)*math.sin(abs(q)*math.pi)
        vertices.append(p)
        if r and j:
            k=r*17+j;faces.append((k-18,k-17,k,k-1))
skin('Graphite central nose spine',vertices,faces,'Apex_Graphite',.004,.001)
curved_patch('White central nose point',[(-.016,.818,1.024),(.016,.818,1.024),(.025,.837,1.017),(-.025,.837,1.017)],'Apex_Pearl',rows=2,cols=4)
vertices=[];faces=[]
for r in range(15):
    t=r/14
    for j in range(21):
        q=j/10-1;width=.158-.027*t
        vertices.append((q*width,1.008+.168*t-.036*q*q,.669-.257*t+.048*q*q))
        if r and j:
            k=r*21+j;faces.append((k-22,k-21,k,k-1))
skin('Swept smoked windscreen',vertices,faces,'Apex_Glass',.003,.001)
for side in [-1,1]:
    tube('Windscreen fitted rubber rim',[(side*(.158-.027*t),1.008+.168*t-.036,.669-.257*t+.048) for t in [j/16 for j in range(17)]],.0024,'Apex_Graphite',sides=6)
    for t in [.05,.29,.51]:
        sphere('Screen fixing screw',(side*(.158-.027*t),1.011+.168*t-.036,.669-.257*t+.048),(.006,.006,.006),'Apex_Machined',segments=10,rings=6)

# Traced concept proportion correction: painted nose ends ~0.10m ahead of
# axle, not at the outer end of the tyre. This retains exact component join
# coordinates by warping every nose subcomponent through the same function.
for obj in parts[nose_parts_start:]:
    world=obj.matrix_world.copy();inv=world.inverted()
    for vertex in obj.data.vertices:
        p=world@vertex.co;forward=p.y
        p.y=.48+(forward-.48)*.63
        p.z-=.06*max(0,min(1,(forward-.48)/.54))
        vertex.co=inv@p
    obj.data.update()

for side in [-1,1]:
    curved_patch('Fitted shoulder nose bridge',[(side*.209,.960,.580),(side*.222,.799,.776),(side*.236,.824,.744),(side*.242,.905,.580)],'Apex_Pearl',rows=6,cols=8,bulge=.001)
