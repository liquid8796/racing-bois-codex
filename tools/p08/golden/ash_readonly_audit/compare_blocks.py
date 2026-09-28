"""Inspect two preserved blend streams without importing bpy or starting Blender."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import sys
import zstandard

ROOT=Path(__file__).resolve().parents[4]
MODULES=Path('C:/Program Files/Blender Foundation/Blender 5.2/5.2/scripts/modules')
sys.path.insert(0,str(MODULES))
from _blendfile_header import BlendFileHeader,BlockHeader

CURRENT=ROOT/'ArtSource/P08/Golden/Ash/V7R2/RB_Golden_Ash_V7R2.blend'
BASELINE=CURRENT.with_suffix('.blend1')
HASHES={BASELINE:'472b1c44108999a4fd634795885db3ccc7afbdc230e4fa7885b8e9bb97426bb0',
        CURRENT:'6d689a5df0ddf9de97d249bd4f56fd8a4e7bba844af80fc44a11c54fd428dcd8'}
def digest(data): return hashlib.sha256(data).hexdigest()
def dna(data):
    pos=0
    def expect(value):
        nonlocal pos
        assert data[pos:pos+len(value)]==value
        pos+=len(value)
    def number(format):
        nonlocal pos
        value=struct.unpack_from('<'+format,data,pos)[0];pos+=struct.calcsize(format);return value
    def strings(count):
        nonlocal pos
        result=[]
        for _ in range(count):
            end=data.index(0,pos);result.append(data[pos:end].decode('utf-8'));pos=end+1
        pos=(pos+3)&~3
        return result
    expect(b'SDNANAME');names=strings(number('I'))
    expect(b'TYPE');types=strings(number('I'))
    expect(b'TLEN');sizes=[number('H') for _ in types];pos=(pos+3)&~3
    expect(b'STRC');structures=[]
    for _ in range(number('I')):
        typename=number('H');fields=[(number('H'),number('H')) for _ in range(number('H'))]
        structures.append(dict(type=types[typename],size=sizes[typename],fields=[(types[t],names[n],sizes[t]) for t,n in fields]))
    assert pos==len(data)
    return structures

def read(path):
    compressed=path.read_bytes();assert digest(compressed)==HASHES[path]
    blocks=[]
    with zstandard.open(path,'rb') as stream:
        header=BlendFileHeader(stream);layout=header.create_block_header_struct()
        while True:
            block=BlockHeader(stream,layout)
            if block.code==b'ENDB':break
            chunks=[];remaining=block.size
            while remaining:
                chunk=stream.read(remaining)
                if not chunk:raise ValueError(f'Truncated block {len(blocks)} {block.code!r} expected={block.size} missing={remaining} offset={stream.tell()}')
                chunks.append(chunk);remaining-=len(chunk)
            payload=b''.join(chunks)
            blocks.append(dict(code=block.code.decode('ascii'),address=block.addr_old,sdna=block.sdna_index,
                               count=block.count,size=block.size,hash=digest(payload),data=payload))
    definitions=dna(next(block['data'] for block in blocks if block['code']=='DNA1'))
    for block in blocks:
        block['type']=definitions[block['sdna']]['type'] if 0<=block['sdna']<len(definitions) else '?'
    return header,blocks,definitions

def main():
    before=read(BASELINE);after=read(CURRENT)
    def index(blocks):
        seen=collections.Counter();result={}
        for block in blocks:
            key=(block['code'],block['address']);ordinal=seen[key];seen[key]+=1
            result[(*key,ordinal)]=block
        return result,{str(key):count for key,count in seen.items() if count>1}
    old,old_duplicates=index(before[1]);new,new_duplicates=index(after[1])
    matched=old.keys()&new.keys()
    changed=[(old[key],new[key]) for key in matched if old[key]['hash']!=new[key]['hash']]
    result=dict(schema=1,scope='Read-only serialized block comparison; no bpy/Blender execution, export, ownership inference or visual acceptance.',
                baseline=dict(path=BASELINE.relative_to(ROOT).as_posix(),sha256=HASHES[BASELINE],bytes=BASELINE.stat().st_size),
                current=dict(path=CURRENT.relative_to(ROOT).as_posix(),sha256=HASHES[CURRENT],bytes=CURRENT.stat().st_size),
                reader=dict(path=str(MODULES/'_blendfile_header.py'),sha256=digest((MODULES/'_blendfile_header.py').read_bytes()),zstandardVersion=zstandard.__version__),
                headers=[dict(version=value[0].version,fileFormat=value[0].file_format_version,pointerSize=value[0].pointer_size) for value in [before,after]],
                dnaExact=before[2]==after[2],blocksBefore=len(old),blocksAfter=len(new),matchingBlockAddresses=len(matched),
                duplicateAddressOccurrencesBefore=old_duplicates,duplicateAddressOccurrencesAfter=new_duplicates,
                unchangedMatchingBlocks=len(matched)-len(changed),changedMatchingBlocks=len(changed),
                changedTypes=dict(collections.Counter(pair[0]['type'] for pair in changed)),
                missingTypes=dict(collections.Counter(old[key]['type'] for key in old.keys()-new.keys())),
                addedTypes=dict(collections.Counter(new[key]['type'] for key in new.keys()-old.keys())),
                changed=[dict(code=a['code'],address=a['address'],type=a['type'],beforeBytes=a['size'],afterBytes=b['size'],beforeHash=a['hash'],afterHash=b['hash']) for a,b in changed])
    assert all(digest(path.read_bytes())==value for path,value in HASHES.items())
    out=ROOT/'docs/p08/golden/ash/v7r2-local-audit/block-comparison.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise ValueError('Fresh audit output required')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key not in {'changed','reader','baseline','current'}}))

if __name__=='__main__':main()
