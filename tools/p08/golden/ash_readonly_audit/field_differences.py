"""Describe SDNA field changes; preserve and report pointer changes rather than guessing."""
import collections
import hashlib
import json
import math
import re
import struct
from compare_blocks import read,BASELINE,CURRENT,ROOT,HASHES

def size(field):
    typename,name,length=field
    count=math.prod(map(int,re.findall(r'\[(\d+)\]',name)))
    return (8 if '*' in name else length)*count
def field_name(name):return re.sub(r'\[.*','',name).lstrip('*')
def index(blocks):
    seen=collections.Counter();result={}
    for block in blocks:
        key=(block['code'],block['address']);ordinal=seen[key];seen[key]+=1;result[(*key,ordinal)]=block
    return result
def brief(field,data):
    typename,name,_=field
    if '*' in name:
        values=list(struct.unpack('<'+'Q'*(len(data)//8),data))
        return dict(pointer=True,values=values[:8],count=len(values))
    if typename=='char':
        return data.split(b'\0')[0].decode('utf-8',errors='replace') if len(data)<1024 else dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    formats={'float':'f','double':'d','int':'i','uint':'I','short':'h','ushort':'H','int8_t':'b','uint8_t':'B','int16_t':'h','uint16_t':'H','int32_t':'i','uint32_t':'I','int64_t':'q','uint64_t':'Q','char':'b'}
    fmt=formats.get(typename)
    if fmt and len(data)<=128:
        values=list(struct.unpack('<'+fmt*(len(data)//struct.calcsize(fmt)),data))
        return values
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

def main():
    old_header,old_blocks,defs=read(BASELINE);new_header,new_blocks,new_defs=read(CURRENT)
    assert defs==new_defs
    definitions={row['type']:row for row in defs}
    invalid={row['type']:(row['size'],sum(size(field) for field in row['fields'])) for row in defs if row['size']!=sum(size(field) for field in row['fields'])}
    def walk(typename,old,new,prefix=''):
        definition=definitions[typename]
        if typename in invalid:
            yield dict(path=prefix or typename,type=typename,layoutUnresolved=True)
            return
        offset=0
        for field in definition['fields']:
            length=size(field);left,right=old[offset:offset+length],new[offset:offset+length];offset+=length
            if left==right:continue
            kind,name,unit=field;name=field_name(name);path=prefix+'.'+name if prefix else name
            if '*' not in field[1] and kind in definitions:
                assert length%unit==0
                for part in range(length//unit):
                    a,b=left[part*unit:(part+1)*unit],right[part*unit:(part+1)*unit]
                    if a!=b:yield from walk(kind,a,b,path+(f'[{part}]' if length!=unit else ''))
            else:yield dict(path=path,type=kind,pointer='*' in field[1],before=brief(field,left),after=brief(field,right))
    def name(block):
        definition=definitions[block['type']]
        if not definition['fields'] or definition['fields'][0][0]!='ID':return None
        offset=0
        for field in definitions['ID']['fields']:
            if field_name(field[1])=='name':return block['data'][offset:offset+size(field)].split(b'\0')[0].decode('utf-8',errors='replace')
            offset+=size(field)
        return None
    old,new=index(old_blocks),index(new_blocks)
    changes=[];counts=collections.Counter();unparsed=[]
    for key in old.keys()&new.keys():
        a,b=old[key],new[key]
        if a['hash']==b['hash']:continue
        if a['type']!=b['type'] or a['size']!=b['size'] or a['size']!=a['count']*definitions[a['type']]['size']:
            unparsed.append(dict(code=a['code'],type=a['type'],beforeSize=a['size'],afterSize=b['size'],reason='Size/count/type not a complete structured array'));continue
        unit=definitions[a['type']]['size'];fields=[]
        for part in range(a['count']):
            left,right=a['data'][part*unit:(part+1)*unit],b['data'][part*unit:(part+1)*unit]
            if left!=right:
                for row in walk(a['type'],left,right):
                    counts[a['type']+'.'+row['path']]+=1
                    fields.append(row)
        changes.append(dict(code=a['code'],type=a['type'],name=name(a),address=a['address'],fields=fields))
    result=dict(schema=1,scope='Exact SDNA field comparison where summed serialized field sizes match TLEN; changed pointers remain unresolved references, not proof of unchanged bindings.',
                sourceHashes={str(path.relative_to(ROOT)):value for path,value in HASHES.items()},unresolvedLayouts=invalid,
                changedFieldCounts=dict(counts.most_common()),structuredChangedBlocks=changes,unparsedChangedBlocks=unparsed)
    assert all(hashlib.sha256(path.read_bytes()).hexdigest()==value for path,value in HASHES.items())
    out=ROOT/'docs/p08/golden/ash/v7r2-local-audit/field-differences.json'
    if out.exists():raise ValueError('Fresh field audit output required')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(unresolvedLayouts=invalid,changedFieldCounts=dict(counts.most_common(65)),unparsedChangedBlocks=len(unparsed))))

if __name__=='__main__':main()
