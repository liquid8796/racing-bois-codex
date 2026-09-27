import bpy,json,math
path='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/Sky/qwantani_sunset_puresky_4k.hdr'
image=bpy.data.images.load(path,check_existing=True);image.reload()
copy=image.copy();copy.name='Canyon_HDRI_Inspection';copy.scale(512,256)
pixels=list(copy.pixels)
def luminance(i):return pixels[i*4]*.2126+pixels[i*4+1]*.7152+pixels[i*4+2]*.0722
index=max(range(len(pixels)//4),key=luminance)
u=(index%512+.5)/512;v=(index//512+.5)/256
print('CANYON_HDRI_SUN '+json.dumps({'u':u,'v':v,'azimuthRadians':u*math.pi*2-math.pi,'elevationRadians':(v-.5)*math.pi,'maxLuminance':pixels[index*4]*.2126+pixels[index*4+1]*.7152+pixels[index*4+2]*.0722}))
copy.save_render('D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v13/hdri-inspection.png',scene=bpy.context.scene)
bpy.data.images.remove(copy)
