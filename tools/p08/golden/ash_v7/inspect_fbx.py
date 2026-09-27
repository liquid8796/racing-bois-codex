"""Read-only binary FBX Model property comparison; does not run Blender code."""
from pathlib import Path
import struct,json,hashlib

ROOT=Path(__file__).resolve().parents[4]
def read_models(path):
    data=path.read_bytes()
    assert data.startswith(b'Kaydara FBX Binary  \x00\x1a\x00')
    version=struct.unpack_from('<I',data,23)[0]
    header=struct.Struct('<QQQB' if version>=7500 else '<IIIB')
    def prop(offset):
        code=chr(data[offset]);offset+=1
        scalar={'Y':'h','C':'?','I':'i','F':'f','D':'d','L':'q'}
        if code in scalar:
            fmt=struct.Struct('<'+scalar[code]);return fmt.unpack_from(data,offset)[0],offset+fmt.size
        if code in ['S','R']:
            size=struct.unpack_from('<I',data,offset)[0];offset+=4;value=data[offset:offset+size]
            return value.decode('utf-8','replace') if code=='S' else '<binary>',offset+size
        if code in 'fdilbc':
            length,encoding,size=struct.unpack_from('<III',data,offset)
            return '<array>',offset+12+size
        raise ValueError('Unknown FBX property '+repr(code))
    def node(offset):
        end,count,length,name_size=header.unpack_from(data,offset)
        if not end:return None,offset+header.size
        offset+=header.size;name=data[offset:offset+name_size].decode();offset+=name_size;properties=[]
        for _ in range(count):value,offset=prop(offset);properties.append(value)
        children=[]
        while offset<end:
            child,offset=node(offset)
            if child is None:break
            children.append(child)
        return {'name':name,'properties':properties,'children':children},end
    roots=[];offset=27
    while offset+header.size<len(data):
        current,offset=node(offset)
        if current is None:break
        roots.append(current)
    objects=next(n for n in roots if n['name']=='Objects');result={}
    wanted=['RB_P06_Rider_L0_Hip','RB_P06_Rider_L0_Torso','RB_P06_Rider_L0_Head','RB_P06_Rider_L0_UpperArm_L','RB_P06_Rider_L0_Forearm_L']
    for model in objects['children']:
        if model['name']!='Model':continue
        name=model['properties'][1].split('\x00')[0]
        if name not in wanted:continue
        props=next((p for p in model['children'] if p['name']=='Properties70'),None)
        if props:
            result[name]={p['properties'][0]:p['properties'][4:] for p in props['children'] if p['name']=='P' and p['properties'][0] in ['Lcl Translation','Lcl Rotation','Lcl Scaling','PreRotation']}
    stacks=[node['properties'][1].split('\x00')[0] for node in objects['children'] if node['name']=='AnimationStack']
    takes=next((node for node in roots if node['name']=='Takes'),None)
    current=next((node['properties'] for node in takes['children'] if node['name']=='Current'),[]) if takes else []
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'version':version,'models':result,'animationStackOrder':stacks,'currentTake':current}
result=read_models(ROOT/'_local/p08-ash-v7-staging/RB_Golden_Ash_V7.fbx')
(ROOT/'docs/p08/golden/ash/v7/fbx-inspection.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'animationStackOrder':result['animationStackOrder'],'currentTake':result['currentTake']}))
