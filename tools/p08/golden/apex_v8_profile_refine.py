"""Correct upper-body overhangs from the actual concept, preserving wheelbase.

This literal tail of the recipe runs before collection assembly and save.
"""
for obj in parts:
    name=obj.name
    tail = any(name.startswith(prefix) for prefix in ['Contoured rider saddle','Tapered white tail shell','Elevated compact passenger saddle','Saddle tailored perimeter','Rear side black vent insert','Subframe upper rail','Subframe triangulation'])
    pipe = any(name.startswith(prefix) for prefix in ['Under-seat exhaust riser','Twin exhaust branch','Under-seat titanium silencer','Hollow silencer end collar','Dark inner exhaust wall','Recessed dark throat','Exhaust hanging strap'])
    led = name.startswith('Rear LED housing') or name.startswith('Continuous rear LED')
    if not (tail or pipe or led):continue
    world=obj.matrix_world.copy();inv=world.inverted()
    for vertex in obj.data.vertices:
        p=world@vertex.co
        z=p.y
        if tail and z<-.55 and p.z>.70:
            t=min(1,(-z-.55)/.45)
            p.y=-.55+(z+.55)*.57;p.z+=.07*t
        if pipe:
            t=max(0,min(1,(-z-.40)/.30))
            rear=max(0,min(1,(-z-.72)/.28))
            p.y+=.17*t;p.z+=(-.065+.10*rear)*t
        if led:
            p.y+=.197;p.z+=.028
        vertex.co=inv@p
    obj.data.update()
