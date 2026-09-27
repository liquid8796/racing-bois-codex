"""P08 original authoring extensions; geometry only after matching concept review."""
import random

def torus(name,pos,major,minor,tile,mat,segments=40,minor_segments=8,axis='X'):
    # The shared primitive helper names Blender axes. P08 recipes name semantic
    # Unity axes: Y-up maps to Blender Z; forward-Z maps to Blender -Y.
    rotation=(0,math.pi/2,0) if axis=='X' else (0,0,0) if axis=='Y' else (math.pi/2,0,0)
    bpy.ops.mesh.primitive_torus_add(major_segments=segments,minor_segments=minor_segments,major_radius=major,minor_radius=minor,location=bv(pos),rotation=rotation)
    return finish(bpy.context.object,name,tile,mat)

def hash2(x,y,seed):
    value=(x*374761393+y*668265263+seed*1442695041)&4294967295
    value=((value^(value>>13))*1274126177)&4294967295
    return ((value^(value>>16))&65535)/65535

def value_noise(u,v,res,seed):
    x=u*res;y=v*res;ix=math.floor(x);iy=math.floor(y);a=x-ix;b=y-iy
    a=a*a*(3-2*a);b=b*b*(3-2*b)
    p=hash2(ix,iy,seed)*(1-a)+hash2(ix+1,iy,seed)*a
    q=hash2(ix,iy+1,seed)*(1-a)+hash2(ix+1,iy+1,seed)*a
    return p*(1-b)+q*b

def procedural_grain(x,y,dim,surface):
    u=(x*4/dim)%1;v=(y*4/dim)%1;seed=x//(dim//4)+4*(y//(dim//4))+808
    macro=value_noise(u,v,7,seed)*2-1;aggregate=value_noise(u,v,53,seed+7)*2-1;micro=hash2(x,y,seed+31)*2-1
    if surface=='wood':return .35*macro+.25*aggregate+.12*micro+.28*math.sin(u*math.tau*24+macro*2)
    return .57*macro+.29*aggregate+.14*micro

def profile(name, outline, width, tile, mat, bevel=.012, centerx=0):
    vertices=[bv((x,y,z)) for x in [centerx-width/2,centerx+width/2] for y,z in outline]
    n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    return finish(obj,name,tile,mat,bevel)

def p08_begin(batch):
    bpy.ops.wm.save_as_mainfile(filepath=ROOT+'_local/p08-before-'+batch+'.blend')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    return scene

def authored_lods(parts, name, root, ratios=(.5,.2)):
    body=join(parts,name+'_L0_Body',root)
    for level,ratio in enumerate(ratios,1):lod_copy(body,name+'_L'+str(level)+'_Body',ratio,root)
    export(root,name)
    for obj in root.children_recursive:
        if obj.type=='MESH':obj.hide_render=True
    return body

def asset_report(root, concept, surface, kind, source, collider=True):
    lods=[]
    for level in range(3):
        meshes=[o for o in root.children_recursive if o.type=='MESH' and '_L'+str(level)+'_' in o.name]
        for obj in meshes:obj.data.calc_loop_triangles()
        lods.append({'level':level,'triangles':sum(len(o.data.loop_triangles) for o in meshes),'renderers':len(meshes)})
    return {'name':root.name,'concept':concept,'source':source,'fbx':'Assets/RacingBois/Art/P08/'+root.name+'.fbx',
            'surface':surface,'kind':kind,'primitiveCollider':collider,'lods':lods,
            'uvPolicy':'Material tiles intentionally shared across disconnected manufactured components; audited within each connected component.'}

def save_pack(batch, reports, camera=(15,12,19), target=(0,4,0)):
    source=ROOT+'ArtSource/P08/RB_P08_'+batch+'.blend'
    bpy.ops.wm.save_as_mainfile(filepath=source)
    # Contact renders are a temporary arrangement; saved sources preserve identity roots.
    roots=[bpy.data.objects[r['name']] for r in reports]
    def height(root):
        return max((obj.matrix_world@Vector(c)).z for obj in root.children_recursive if obj.type=='MESH' for c in obj.bound_box)
    roots.sort(key=height)
    spacing=16 if batch=='neon' else 12
    for i,root in enumerate(roots):
        root.location=bv(((i%3-1)*spacing,0,(i//3)*-spacing))
        for obj in root.children_recursive:
            if obj.type=='MESH':obj.hide_render='_L0_' not in obj.name
    studio(target=(0,3,-spacing*.4),camera_pos=(spacing*2.25,spacing*1.45,spacing*2.6),resolution=(1536,1024))
    camera=bpy.context.scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=spacing*3.8
    bpy.context.scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.22,.25,.29,1)
    bpy.context.scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.85
    for light in [o for o in bpy.context.scene.objects if o.type=='LIGHT']:
        light.location*=8;light.data.energy*=36;light.data.size*=8
    bpy.context.scene.render.film_transparent=False
    bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=16
    bpy.context.scene.render.filepath=ROOT+'docs/p08/art/'+batch+'-contact.png'
    bpy.ops.render.render(write_still=True)
    for root in roots:root.location=(0,0,0)
    print(json.dumps({'batch':batch,'assets':reports,'source':source,'conceptFirst':True}))
