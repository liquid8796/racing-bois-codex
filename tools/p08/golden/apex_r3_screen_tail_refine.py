"""Apply measured rim and rear-light corrections to the current editable R3."""
import bpy,math,json
from mathutils import Vector
root=bpy.data.objects['RB_Golden_Apex_r3']
def nose_z(x,y):return .835-.38*(y-.855)-.31*abs(x)-.18*max(0,(y-.952)/.064)**1.2
screen=bpy.data.objects['R3 Swept attached smoked screen'];data=screen.data
# Source grid order is preserved by solidify: surface then reverse shell.
for vertex in data.vertices:
    k=vertex.index%(15*23);r=k//23;j=k%23;q=j/11-1;t=r/14;width=.151-.022*t
    oldbase_y=1.010-.038*q*q;oldbase_z=nose_z(q*.151,oldbase_y)+.002
    old=Vector((q*width,oldbase_z-.185*t,oldbase_y+.118*t+.018*q*q*t))
    base_y=.983-.011*q*q;base_z=nose_z(q*.151,base_y)+.002
    new=Vector((q*width,base_z-.230*t,base_y+.145*t-.009*q*q*t))
    vertex.co+=new-old
data.update()
# Rim tubes have8 vertices per longitudinal sample. Keep the actual radius.
for side in [-1,1]:
    obj=bpy.data.objects['R3 Screen fitted rim '+str(side)]
    for v in obj.data.vertices:
        sample=min(16,v.index//8);t=sample/16;v.co.y-=.045*t
    obj.data.update()
obj=bpy.data.objects['R3 Screen base seated gasket']
for v in obj.data.vertices:
    sample=min(32,v.index//8);q=sample/16-1
    oldy=1.010-.038*q*q;newy=.983-.011*q*q
    v.co.z+=newy-oldy;v.co.y+=nose_z(q*.151,newy)-nose_z(q*.151,oldy)
obj.data.update()
# The inherited LED was hidden by the newly closed tail. Move the actual
# existing housing/strip to the back surface rather than introducing a decal.
for name,center in [('Rear LED housing',(0,1.004,-.909)),('Continuous rear LED',(0,1.005,-.917))]:
    o=bpy.data.objects[name];world=o.matrix_world.copy();inv=world.inverted();actual=sum((world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices);target=Vector((center[0],center[2],center[1]))
    for v in o.data.vertices:v.co=inv@(world@v.co+target-actual)
    o.data.update()
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend')
print('APEX_R3_RIM_REFINEMENT '+json.dumps({'screenConvexTowardFront':True,'baseTracksCowl':True,'rearLightExposedAtNewTail':True,'visualAccepted':False}))
