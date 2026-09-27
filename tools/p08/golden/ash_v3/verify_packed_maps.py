"""Read saved .blend blocks and verify exact packed PNG bytes against final maps.

This is read-only binary asset inspection, not Blender execution or addon
registration. It complements live material/image binding and reload receipts.
"""
from pathlib import Path
import struct,hashlib,json,zlib

ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/'ArtSource/P08/Golden/Ash/V3/RB_Golden_Ash_V3.blend'
REPORT=ROOT/'docs/p08/golden/ash/v3'
data=SOURCE.read_bytes()
assert data[:7]==b'BLENDER','Packed verification requires an uncompressed saved .blend'
offset=0;packed=[];signature=b'\x89PNG\r\n\x1a\n'
# Blender 5.2 uses the new BLENDER17-01v0502 header/block format. Instead of
# guessing SDNA offsets, validate complete PNG streams by their PNG chunk CRCs
# and compare exact bytes. Live PackedFile ownership is recorded by MCP.
while True:
    start=data.find(signature,offset)
    if start<0:break
    pos=start+8;valid=True;first=True
    while pos+12<=len(data):
        length=struct.unpack_from('>I',data,pos)[0];kind=data[pos+4:pos+8]
        end=pos+12+length
        if end>len(data) or length>268435456 or (first and kind!=b'IHDR'):
            valid=False;break
        first=False
        expected=struct.unpack_from('>I',data,pos+8+length)[0]
        if zlib.crc32(data[pos+4:pos+8+length])&0xffffffff!=expected:
            valid=False;break
        pos=end
        if kind==b'IEND':
            raw=data[start:pos];packed.append({'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'byteOffset':start});break
    offset=pos if valid else start+len(signature)
known={item['sha256'] for item in packed}
descriptor=json.loads((REPORT/'descriptor-bind.json').read_text())
asset=descriptor['assets'][0]
rows=[]
for material in asset['materials']:
    for channel in ['baseColor','normal','metallicSmoothness','occlusion']:
        entry=material[channel];digest=hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()
        rows.append({'material':material['sourceName'],'channel':channel,'path':entry['path'],'externalSha256':digest,'manifestUnchanged':digest==entry['sha256'],'samePngBytesPacked':digest in known})
result={'source':SOURCE.relative_to(ROOT).as_posix(),'sourceSha256':hashlib.sha256(data).hexdigest(),'sourceMatchesDescriptor':hashlib.sha256(data).hexdigest()==asset['source']['sha256'],'scope':'Read-only exact CRC-validated PNG stream membership plus material live binding receipts. Not a visual similarity claim.','packedPngStreams':len(packed),'files':rows,'passed':all(r['manifestUnchanged'] and r['samePngBytesPacked'] for r in rows)}
result['passed']=result['passed'] and result['sourceMatchesDescriptor']
(REPORT/'packed-texture-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'files':len(rows),'sourceSha256':result['sourceSha256']}))
if not result['passed']:raise SystemExit(1)
