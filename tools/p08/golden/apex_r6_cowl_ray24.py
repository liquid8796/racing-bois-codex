import bpy
import json
from mathutils import Vector
origin=Vector((0,4.5,.85));rotation=(Vector((0,0,.61))-origin).to_track_quat('-Z','Y')
right=rotation@Vector((1,0,0));up=rotation@Vector((0,1,0));direction=rotation@Vector((0,0,-1))
rows=[];deps=bpy.context.evaluated_depsgraph_get()
for px,py in [(540,348),(560,346),(580,337),(600,340),(619,349),(640,336),(660,349),(680,340),(700,337),(720,346),(740,348)]:
    start=origin+right*((px+.5)/1280-.5)*2.5+up*(.5-(py+.5)/900)*(2.5*900/1280)
    hits=[]
    for step in range(4):
        hit,point,normal,index,obj,matrix=bpy.context.scene.ray_cast(deps,start,direction)
        if not hit:break
        hits.append({'name':obj.name,'position':list(point)})
        start=point+direction*.0002
    rows.append({'pixel':[px,py],'layers':hits})
print('COWL_RAYS='+json.dumps(rows))
