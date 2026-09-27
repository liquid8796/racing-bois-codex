import bpy,math,json
from mathutils import Vector
scene=bpy.context.scene
mapping=next(n for n in scene.world.node_tree.nodes if n.type=='MAPPING')
# Measured against eight actual background-only renders, not assumed UV yaw.
mapping.inputs['Rotation'].default_value[2]=4.447
azimuth=2*math.pi-.632000084608884-4.447
elevation=.1043106935762236
direction=Vector((math.cos(azimuth)*math.cos(elevation),math.sin(azimuth)*math.cos(elevation),math.sin(elevation)))
sun=bpy.data.objects['Canyon_WarmSun'];sun.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_percentage=100;scene.cycles.samples=32
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v13/gameplay-final.png'
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/V13/RB_Golden_Canyon_lighting.blend')
print('CANYON_LIGHTING '+json.dumps({'hdri':'Assets/RacingBois/Art/P08/Golden/Canyon/V13/Sky/qwantani_sunset_puresky_4k.hdr','blenderMappingZRadians':4.447,'measuredSunTextureUv':[.6005859375,.533203125],'sunDirectionToLightUnity':[direction.x,direction.z,direction.y],'blenderSunEnergy':sun.data.energy,'sunColorLinear':list(sun.data.color),'sunAngularDiameterDegrees':math.degrees(sun.data.angle),'blenderWorldStrength':.85,'cameraPositionUnity':[1.7,1.55,3],'cameraTargetUnity':[-2,-2.6,32],'cameraFocalLengthMm':28,'sensorWidthMm':36,'aspect':2,'fogDensity':.0008,'fogColorLinear':[.60,.58,.53],'scope':'Blender capture recipe; Unity equivalent intensity/sky rotation/fog requires actual native visual matching.'}))
