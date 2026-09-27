import bpy,json
expected='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend'
assert bpy.data.filepath.replace('\\','/')==expected,'Only unpublished R1 source may be resaved'
compress_option=bpy.ops.wm.save_as_mainfile.get_rna_type().properties['compress']
assert compress_option.type=='BOOLEAN','Native lossless compression contract changed'
bpy.ops.wm.save_as_mainfile(filepath=expected,compress=True)
print('V7R1_NATIVE_COMPRESSION '+json.dumps({'source':expected,'nativeCompress':True,'originalV7Untouched':True,'uncompressedR1PreservedInPrivateStaging':True}))
