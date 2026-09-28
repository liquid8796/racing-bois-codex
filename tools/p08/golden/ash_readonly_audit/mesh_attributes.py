"""Resolve mesh attributes within their owning ID's DATA-block scope."""
import collections
import hashlib
import json
import struct
from compare_blocks import read,BASELINE,CURRENT,ROOT,HASHES
from field_differences import size,field_name

def inspect(path):
    _,blocks,rows=read(path);defs={row['type']:row for row in rows}
    offsets={}
    for row in rows:
        offset=0;fields={}
        for field in row['fields']:
            fields[field_name(field[1])]=(offset,size(field),field);offset+=size(field)
        assert offset==row['size'];offsets[row['type']]=fields
    def get(kind,data,path):
        parts=path.split('.');offset,length,field=offsets[kind][parts[0]];value=data[offset:offset+length]
        if len(parts)>1:return get(field[0],value,'.'.join(parts[1:]))
        return value
    def pointer(kind,data,path):return struct.unpack('<Q',get(kind,data,path))[0]
    def number(kind,data,path,fmt='i'):return struct.unpack('<'+fmt,get(kind,data,path))[0]
    def named(block):
        fields=defs[block['type']]['fields']
        return bool(fields and fields[0][0]=='ID' and fields[0][1]=='id')
    groups={};group=None
    global_addresses=collections.defaultdict(list)
    for block in blocks:
        global_addresses[block['address']].append(block)
        if block['code']!='DATA' and named(block):
            name=get(block['type'],block['data'],'id.name').split(b'\0')[0].decode('utf-8');assert name not in groups
            group=dict(root=block,blocks=[]);groups[name]=group
        if group is not None:group['blocks'].append(block)
    meshes={};unresolved=[]
    for name,group in groups.items():
        root=group['root']
        if root['type']!='Mesh':continue
        local=collections.defaultdict(list)
        for block in group['blocks']:local[block['address']].append(block)
        def resolve(address,expected=None):
            candidates=local.get(address,[]) or global_addresses.get(address,[])
            if expected:candidates=[block for block in candidates if block['type']==expected]
            unique={(block['type'],block['size'],block['hash']):block for block in candidates}
            if len(unique)!=1:raise ValueError(f'{name}: unresolved address {address} expected={expected} candidates={len(unique)}')
            return next(iter(unique.values()))
        try:
            count=number('Mesh',root['data'],'attribute_storage.dna_attributes_num')
            owner=resolve(pointer('Mesh',root['data'],'attribute_storage.dna_attributes'),'Attribute')
            assert owner['count']==count and owner['size']==count*defs['Attribute']['size']
            attributes={};ordering=[]
            for index in range(count):
                data=owner['data'][index*24:(index+1)*24]
                attrname=resolve(pointer('Attribute',data,'name'))['data'].split(b'\0')[0].decode('utf-8')
                assert attrname not in attributes;ordering.append(attrname)
                storage=resolve(pointer('Attribute',data,'data'))
                assert storage['type'] in {'AttributeArray','AttributeSingle'}
                payload=resolve(pointer(storage['type'],storage['data'],'data'))
                attributes[attrname]=dict(dataType=number('Attribute',data,'data_type','h'),domain=number('Attribute',data,'domain','b'),
                    storageType=number('Attribute',data,'storage_type','b'),storageClass=storage['type'],
                    count=number('AttributeArray',storage['data'],'size','q') if storage['type']=='AttributeArray' else 1,
                    isSingle=number('AttributeArray',storage['data'],'is_single','b') if storage['type']=='AttributeArray' else 1,
                    payloadType=payload['type'],payloadBytes=payload['size'],payloadSha256=payload['hash'])
            poly=pointer('Mesh',root['data'],'poly_offset_indices')
            meshes[name]=dict(counts={field:number('Mesh',root['data'],field) for field in ['totvert','totedge','totpoly','totloop']},
                              polygonOffsetsSha256=resolve(poly)['hash'] if poly else None,attributes=attributes,attributeOrder=ordering)
        except (ValueError,AssertionError) as error:unresolved.append(dict(mesh=name,error=str(error)))
    # Exact group content check for other authored data; only declared runtime ID
    # counters are zeroed. Addresses are retained, so pointer changes cannot hide.
    fingerprints={}
    for name,group in groups.items():
        root=group['root']
        if root['type'] not in {'bAction','Material','Image','bArmature','Key','Camera','World'}:continue
        values=[]
        for block in group['blocks']:
            data=bytearray(block['data'])
            if named(block):
                for field in ['session_uid','recalc_up_to_undo_push','recalc_after_undo_push']:
                    offset,length,_=offsets['ID'][field];data[offset:offset+length]=bytes(length)
            values.append((block['code'],block['type'],block['address'],block['count'],len(data),hashlib.sha256(data).hexdigest()))
        fingerprints[name]=dict(type=root['type'],blocks=len(values),sha256=hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest())
    return meshes,unresolved,fingerprints

def main():
    old,old_errors,old_groups=inspect(BASELINE);new,new_errors,new_groups=inspect(CURRENT)
    changes=[]
    for name in old.keys()|new.keys():
        if old.get(name)!=new.get(name):changes.append(dict(mesh=name,before=old.get(name),after=new.get(name)))
    group_changes=[dict(id=name,before=old_groups.get(name),after=new_groups.get(name)) for name in old_groups.keys()|new_groups.keys() if old_groups.get(name)!=new_groups.get(name)]
    result=dict(schema=1,scope='Owner-scoped resolved mesh-attribute payloads and exact other authored ID groups after excluding only three explicit ID runtime counters. Implicit-sharing handles are not geometry data and are not treated as ownership-equivalent.',
                hashes={str(path.relative_to(ROOT)):value for path,value in HASHES.items()},baselineMeshes=len(old),currentMeshes=len(new),
                baselineUnresolved=old_errors,currentUnresolved=new_errors,meshChanges=changes,
                authoredGroups=len(old_groups),authoredGroupChanges=group_changes)
    assert all(hashlib.sha256(path.read_bytes()).hexdigest()==value for path,value in HASHES.items())
    out=ROOT/'docs/p08/golden/ash/v7r2-local-audit/mesh-attributes.json'
    if out.exists():raise ValueError('Fresh attribute audit output required')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(baselineMeshes=len(old),currentMeshes=len(new),baselineUnresolved=len(old_errors),currentUnresolved=len(new_errors),
                         meshChanges=len(changes),changedMeshNames=[row['mesh'] for row in changes],authoredGroups=len(old_groups),
                         authoredGroupChanges=[row['id'] for row in group_changes],errors=old_errors[:3]+new_errors[:3])))

if __name__=='__main__':main()
