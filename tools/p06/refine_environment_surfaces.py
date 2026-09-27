"""Original stochastic road/gravel surfaces, authored via Blender MCP.

Replaces the early sinusoidal prototype which showed a repeating grid at game
camera distance. The canyon concept remains the approved design reference.
"""
import bpy,math,json
from array import array
ROOT='D:/Project/Unity/racing-bois/'
OUT=ROOT+'Assets/RacingBois/Art/P06/Environment/'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'_local/p06-before-surface-refinement.blend')
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P06/Environment/RB_P06_CanyonKit.blend',use_scripts=False)

def hash2(x,y,seed):
    n=(x*374761393+y*668265263+seed*1442695041)&4294967295
    n=((n^(n>>13))*1274126177)&4294967295
    return ((n^(n>>16))&65535)/65535

def noise(u,v,res,seed):
    x=u*res;y=v*res;ix=math.floor(x);iy=math.floor(y);a=x-ix;b=y-iy
    a=a*a*(3-2*a);b=b*b*(3-2*b)
    p=hash2(ix%res,iy%res,seed)*(1-a)+hash2((ix+1)%res,iy%res,seed)*a
    q=hash2(ix%res,(iy+1)%res,seed)*(1-a)+hash2((ix+1)%res,(iy+1)%res,seed)*a
    return p*(1-b)+q*b

def author(name,gravel):
    rock='Sandstone' in name
    size=1024 if rock else 512;base=array('f');height=array('f');mask=array('f');rough=array('f')
    for y in range(size):
        for x in range(size):
            u=(x+.5)/size;v=(y+.5)/size
            macro=noise(u,v,7,18)-.5;aggregate=noise(u,v,79,43)-.5;micro=hash2(x,y,91)-.5
            if rock:
                strata=math.sin(math.tau*(v*18+.09*noise(u,v,5,23)))
                shade=macro*.045+aggregate*.035+micro*.01+strata*.020
                c=(.40+shade,.245+shade*.73,.125+shade*.45);h=aggregate*.018+strata*.025;r=.91
            elif gravel:
                shade=macro*.048+aggregate*.045+micro*.025
                stone=max(0,(micro-.42)*10)*.035
                c=(.30+shade+stone,.235+shade*.83+stone,.155+shade*.65+stone);h=aggregate*.06+micro*.020;r=.93
            else:
                shade=macro*.015+aggregate*.022+micro*.014
                c=(.092+shade,.103+shade,.107+shade);h=aggregate*.022+micro*.010;r=.88+macro*.025
            base.extend((*c,1));height.append(h);mask.extend((0,1,0,1-r));rough.extend((r,r,r,1))
    normal=array('f')
    for y in range(size):
        for x in range(size):
            nx=(height[y*size+(x-1)%size]-height[y*size+(x+1)%size])*2
            ny=(height[((y-1)%size)*size+x]-height[((y+1)%size)*size+x])*2
            scale=1/math.sqrt(nx*nx+ny*ny+1);normal.extend((.5+.5*nx*scale,.5+.5*ny*scale,.5+.5*scale,1))
    images={}
    for suffix,pixels in [('BaseColor',base),('Normal',normal),('MetallicSmoothness',mask),('Roughness',rough)]:
        im=bpy.data.images.get(name+'_'+suffix)
        if im is None:im=bpy.data.images.new(name+'_'+suffix,size,size,alpha=True)
        if suffix!='BaseColor':im.colorspace_settings.name='Non-Color'
        im.pixels.foreach_set(pixels);im.filepath_raw=OUT+name+'_'+suffix+'.png';im.file_format='PNG';im.save();im.pack();images[suffix]=im
    for mat in bpy.data.materials:
        if not mat.name.startswith(name) or not mat.use_nodes:continue
        for node in mat.node_tree.nodes:
            if node.type!='TEX_IMAGE' or node.image is None:continue
            for suffix,image in images.items():
                if ('_'+suffix) in node.image.name:node.image=image;break
author('RB_P06_Asphalt',False);author('RB_P06_Gravel',True);author('RB_P06_Sandstone',False)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P06/Environment/RB_P06_CanyonKit.blend')
print(json.dumps({'authored':12,'resolution':'Sandstone1024, road/gravel512','source':'periodic seeded value noise and aggregate grains; no image input','concept':'ArtSource/Concepts/P06/canyon-v1.png','normalAmplitudeBounded':True,'original':True}))
