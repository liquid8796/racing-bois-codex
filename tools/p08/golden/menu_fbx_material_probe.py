"""Read the binary FBX material tables/connections without a DCC import."""
from pathlib import Path
import collections
import json
import struct
import zlib
ROOT=Path(__file__).resolve().parents[3]
path=ROOT/'Assets/RacingBois/Art/P08/Golden/MenuEnvironment/V1/RB_Golden_MenuEnvironment.fbx'
data=path.read_bytes();assert data[:23]==b'Kaydara FBX Binary  \x00\x1a\x00'
version=struct.unpack_from('<I',data,23)[0];wide=version>=7500;header=25 if wide else 13
def node(offset):
    end,count,size,n=struct.unpack_from('<QQQB' if wide else '<IIIB',data,offset)
    if not end:return None,offset+header
    p=offset+header;name=data[p:p+n].decode();p+=n;props=[]
    for _ in range(count):
        kind=chr(data[p]);p+=1
        if kind in 'YCLIFD':
            form={'Y':'h','C':'?','L':'q','I':'i','F':'f','D':'d'}[kind]
            props.append(struct.unpack_from('<'+form,data,p)[0]);p+=struct.calcsize(form)
        elif kind in 'SR':
            length=struct.unpack_from('<I',data,p)[0];p+=4
            props.append(data[p:p+length].decode('utf8',errors='replace') if kind=='S' else {'rawBytes':length});p+=length
        elif kind in 'fdlib':
            length,encoding,compressed=struct.unpack_from('<III',data,p);p+=12
            if name=='Materials' and kind=='i':
                raw=data[p:p+compressed];raw=zlib.decompress(raw) if encoding else raw
                props.append(list(struct.unpack('<'+'i'*length,raw)))
            else:props.append({'arrayType':kind,'length':length})
            p+=compressed
        else:raise ValueError('Unknown FBX property '+kind)
    children=[]
    while p<end:
        child,p=node(p)
        if child is None:break
        children.append(child)
    assert p==end,(name,p,end)
    return {'name':name,'properties':props,'children':children},end
nodes=[];offset=27
while True:
    value,offset=node(offset)
    if value is None:break
    nodes.append(value)
objects=next(n for n in nodes if n['name']=='Objects')['children']
by_id={n['properties'][0]:n for n in objects}
connections=next(n for n in nodes if n['name']=='Connections')['children']
def clean(value):return value.split('\x00',1)[0]
report=[]
for model in objects:
    if model['name']!='Model' or not any(k in model['properties'][1] for k in ['Menu_L0_EdgeStone_11','Menu_L0_EdgeStone_12','Menu_L0_EdgeStone_13']):continue
    incoming=[by_id[c['properties'][1]] for c in connections if c['properties'][0]=='OO' and c['properties'][2]==model['properties'][0] and c['properties'][1] in by_id]
    geometry=next(n for n in incoming if n['name']=='Geometry');materials=[n for n in incoming if n['name']=='Material']
    layers=[]
    for layer in geometry['children']:
        if layer['name']!='LayerElementMaterial':continue
        fields={n['name']:n['properties'] for n in layer['children']}
        indices=fields.get('Materials',[[]])[0]
        layers.append({'mapping':fields.get('MappingInformationType'),'reference':fields.get('ReferenceInformationType'),
                       'indexCounts':dict(collections.Counter(indices)),'outOfRange':sum(i<0 or i>=len(materials) for i in indices)})
    report.append({'model':clean(model['properties'][1]),'mesh':clean(geometry['properties'][1]),
                   'materialConnections':[{'id':n['properties'][0],'name':clean(n['properties'][1])} for n in materials],'layers':layers})
out=ROOT/'docs/p08/golden/menu-environment/v2/raw-fbx-materials.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'version':version,'source':path.relative_to(ROOT).as_posix(),'objects':report},indent=2)+'\n')
print(json.dumps(report,indent=2))
