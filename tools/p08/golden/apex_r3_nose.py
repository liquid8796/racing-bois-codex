# One continuous moulded front skin per side, with matching optical boundary.
# All points share the same surface function; no floating brow/cheek overlays.
def nose_z(x,y):
    crown=max(0,(y-.952)/.064)
    return .835-.38*(y-.855)-.31*abs(x)-.18*crown**1.2

outer_xy=[(.012,.838),(.020,.918),(.105,1.016),(.217,.980),(.240,.920),(.229,.848)]
inner_xy=[(.025,.854),(.044,.906),(.177,.947),(.217,.928),(.222,.880),(.191,.855)]
for side in [-1,1]:
    outer=corner_fillets(outer_xy,.10,4);inner=corner_fillets(inner_xy,.12,4);n=len(outer);verts=[];faces=[]
    for k in range(8):
        t=k/7
        for j in range(n):
            x,y=outer[j]*(1-t)+inner[j]*t;verts.append((side*x,y,nose_z(x,y)))
            if k:faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    solid_patch('R3 Unified curved front cowl '+str(side),verts,faces,'Apex_Pearl',.005)
    outline=[Vector((side*x,y,nose_z(x,y))) for x,y in inner]
    center=sum(outline,Vector())/n;opening=[center+(p-center)*.945 for p in outline]
    ringfaces=[(j,(j+1)%n,n+(j+1)%n,n+j) for j in range(n)]
    solid_patch('R3 Moulded optical black lip '+str(side),outline+opening,ringfaces,'Apex_Graphite',.006)
    back=[p-Vector((0,0,.061)) for p in opening]
    solid_patch('R3 Closed dark headlight backing '+str(side),back,[tuple(range(n))],'Apex_Graphite',.004,False)
    solid_patch('R3 Optical cavity depth '+str(side),opening+back,ringfaces,'Apex_Graphite',.003)
    # A compound polycarbonate cover has varying normals, so a softbox does
    # not turn the entire flat aperture into a uniform white reflection.
    normal=Vector((side*.31,.38,1)).normalized();lens_center=sum(opening,Vector())/n;points=[];lensfaces=[]
    for k,scale in enumerate([1,.8,.6,.4,.2]):
        for p in opening:points.append(lens_center+(p-lens_center)*scale+normal*(.001+.006*(1-scale*scale)))
        if k:
            for j in range(n):lensfaces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    ci=len(points);points.append(lens_center+normal*.007)
    for j in range(n):lensfaces.append((4*n+j,4*n+(j+1)%n,ci))
    solid_patch('R3 Compound curved protective lens '+str(side),points,lensfaces,'Apex_Lens',.002,True)
    direction=Vector((side*.10,0,1)).normalized();p=Vector((side*.158,.900,nose_z(.158,.900)-.022))
    bowl('R3 Single projector bezel '+str(side),p,direction,[(-.020,.020),(-.018,.029),(-.005,.030),(-.001,.026),(-.003,.023),(-.018,.017)],'Apex_Machined')
    tube('R3 Single main projector '+str(side),[p-direction*.019,p-direction*.006],.019,'Apex_Lamp',40)
    bowl('R3 Projector lens lip '+str(side),p,direction,[(-.005,.020),(-.002,.021),(.000,.019),(-.001,.018)],'Apex_Graphite')
    # The outer lip lies beyond the lamp aperture and shares its lower edge
    # exactly with the main side fairing's upper edge.
    quad_patch('R3 Cowl side return '+str(side),[(side*.217,.980,nose_z(.217,.980)),(side*.240,.920,nose_z(.240,.920)),(side*fairing_x(.84,.765),.84,.765),(side*fairing_x(.920,.512),.920,.512)],'Apex_Pearl',.003)
    tube('R3 Mirror stalk '+str(side),[(side*.179,.982,.546),(side*.249,1.007,.508),(side*.291,1.052,.475)],.007,'Apex_Graphite',16)
    mirror=[(side*.278,1.039,.475),(side*.377,1.055,.467),(side*.384,1.095,.442),(side*.307,1.100,.430)]
    perimeter=corner_fillets(mirror,.12,5);mc=sum(perimeter,Vector())/len(perimeter);verts=[];faces=[];n=len(perimeter)
    for k,(scale,dz) in enumerate([(.88,.018),(1,.009),(1,-.020),(.90,-.027)]):
        verts.extend([mc+(p-mc)*scale+Vector((0,0,dz)) for p in perimeter])
        if k:
            for j in range(n):faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    faces.extend([tuple(reversed(range(n))),tuple(3*n+j for j in range(n))]);final_mesh('R3 Rounded trapezoid mirror case '+str(side),verts,faces,'Apex_Graphite')
    solid_patch('R3 Recessed rear mirror glass '+str(side),[mc+(p-mc)*.83+Vector((0,0,-.028)) for p in perimeter],[tuple(range(n))],'Apex_Machined',.002,False)

verts=[];faces=[]
for r in range(18):
    t=r/17;y=1.016-(1.016-.838)*t
    width=.020+(.105-.020)*(y-.918)/(.098) if y>=.918 else .012+(.020-.012)*(y-.838)/.080
    for j in range(13):
        x=(j/6-1)*width;verts.append((x,y,nose_z(x,y)+.0005))
        if r and j:k=r*13+j;faces.append((k-14,k-13,k,k-1))
solid_patch('R3 Continuous graphite centre spine',verts,faces,'Apex_Graphite',.004)

verts=[];faces=[]
for r in range(15):
    t=r/14
    for j in range(23):
        q=j/11-1;width=.151-.022*t
        base_y=.983-.011*q*q;base_z=nose_z(q*.151,base_y)+.002
        verts.append((q*width,base_y+.145*t-.009*q*q*t,base_z-.230*t))
        if r and j:k=r*23+j;faces.append((k-24,k-23,k,k-1))
solid_patch('R3 Swept attached smoked screen',verts,faces,'Apex_Glass',.003)
for side in [-1,1]:
    tube('R3 Screen fitted rim '+str(side),[(side*(.151-.022*t),.972+.136*t,nose_z(.151,.972)+.002-.230*t) for t in [i/16 for i in range(17)]],.0027,'Apex_Graphite',8)
tube('R3 Screen base seated gasket',[(q*.151,.983-.011*q*q,nose_z(q*.151,.983-.011*q*q)+.003) for q in [i/16-1 for i in range(33)]],.0033,'Apex_Graphite',8)
