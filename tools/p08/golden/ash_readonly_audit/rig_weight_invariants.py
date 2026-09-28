"""Check exact serialized rig/weight/modifier/curve records, retaining address bindings."""
import collections
import hashlib
import json
from compare_blocks import read,BASELINE,CURRENT,ROOT,HASHES
from field_differences import size,field_name

def inspect(path):
    _,blocks,rows=read(path);definitions={row['type']:row for row in rows}
    def offset(kind,path):
        part,*rest=path.split('.');start=0
        for field in definitions[kind]['fields']:
            if field_name(field[1])==part:
                if rest:
                    nested,length=offset(field[0],'.'.join(rest));return start+nested,length
                return start,size(field)
            start+=size(field)
        raise KeyError(path)
    begin,length=offset('bPoseChannel','runtime.session_uid.uid_')
    counters=collections.defaultdict(collections.Counter)
    elements=collections.Counter()
    for block in blocks:
        kind=block['type']
        if not (kind.startswith('MDeform') or kind in {'bDeformGroup','Bone','bPose','bPoseChannel','BezTriple','FPoint','FCurve','AnimData'} or kind.endswith('ModifierData')):
            continue
        data=bytearray(block['data'])
        if kind=='bPoseChannel':
            assert len(data)==block['count']*definitions[kind]['size']
            for item in range(block['count']):
                start=item*definitions[kind]['size']+begin;data[start:start+length]=bytes(length)
        key=(block['code'],block['address'],block['count'],block['size'],hashlib.sha256(data).hexdigest())
        counters[kind][key]+=1;elements[kind]+=block['count']
    return counters,elements

def main():
    old,old_elements=inspect(BASELINE);new,new_elements=inspect(CURRENT)
    rows=[]
    for kind in sorted(old.keys()|new.keys()):
        before,after=old.get(kind,collections.Counter()),new.get(kind,collections.Counter())
        rows.append(dict(type=kind,blocksBefore=sum(before.values()),blocksAfter=sum(after.values()),
                         elementsBefore=old_elements[kind],elementsAfter=new_elements[kind],
                         exactAfterDeclaredRuntimeUidExclusion=before==after))
    result=dict(schema=1,passed=all(row['exactAfterDeclaredRuntimeUidExclusion'] for row in rows),
                scope='Full record bytes, addresses, counts and multiplicities. Only bPoseChannel.runtime.session_uid.uid_ is excluded; no weight, transform, curve or modifier value is ignored.',
                sourceHashes={str(path.relative_to(ROOT)):value for path,value in HASHES.items()},types=rows)
    assert all(hashlib.sha256(path.read_bytes()).hexdigest()==value for path,value in HASHES.items())
    out=ROOT/'docs/p08/golden/ash/v7r2-local-audit/rig-weight-invariants.json'
    if out.exists():raise ValueError('Fresh invariant output required')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'],types=rows)))

if __name__=='__main__':main()
