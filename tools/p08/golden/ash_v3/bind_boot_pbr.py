"""Bind freshly decoded exact V3 channel maps; never reuse stale image data."""
import bpy,json
records=[]
for role in ['BootLeather','Rubber']:
    material=bpy.data.materials['AshV3_'+role+'_Baked']
    for node in material.node_tree.nodes:
        if node.type!='TEX_IMAGE' or not node.image:continue
        channel=next((value for value in ['BaseColor','Normal','MetallicSmoothness','Occlusion'] if '_'+value in node.image.name),None)
        if channel is None:continue
        path='D:/Project/Unity/racing-bois/Assets/RacingBois/Art/P08/Golden/Ash/V3/Textures/AshV3_'+role+'_'+channel+'.png'
        image=bpy.data.images.load(path,check_existing=False);image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';image.reload();first=tuple(image.pixels[:4]);assert image.has_data;image.pack();node.image=image
        records.append({'material':material.name,'channel':channel,'path':path,'size':list(image.size),'reloadBeforePack':True,'decoded':bool(image.has_data),'packed':bool(image.packed_file)})
print('ASH_V3_BOOT_PBR_BINDINGS '+json.dumps(records))
