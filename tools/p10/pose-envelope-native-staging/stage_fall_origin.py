"""Stage a metadata-only Ash V6 prefab copy outside Assets; do not import or edit art inputs."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
SOURCE_DESCRIPTOR='docs/p08/golden/ash/v6/descriptor.json'
SOURCE_PREFAB='Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Ash_V6.prefab'
CANDIDATE_ID='RB_Golden_Ash_V6_GroundOrigin'

def row(path):
    data=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}

def refs(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):yield value
        for child in value.values():yield from refs(child)
    elif isinstance(value,list):
        for child in value:yield from refs(child)

def write_fresh(path,data):
    if path.exists() and path.read_bytes()!=data:raise ValueError('Refuse to replace a different candidate: '+str(path))
    path.write_bytes(data)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='docs/p10/pose-envelope-native-staging/fall-origin-candidate-v6')
    args=parser.parse_args();output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'docs/p10/pose-envelope-native-staging'):raise ValueError('Candidate must remain in owned staging docs')
    descriptor_path=ROOT/SOURCE_DESCRIPTOR;prefab_path=ROOT/SOURCE_PREFAB
    original=[row(descriptor_path),row(prefab_path)]
    descriptor=json.loads(descriptor_path.read_text())
    if len(descriptor['assets'])!=1 or descriptor['assets'][0]['id']!='RB_Golden_Ash_V6':raise ValueError('Exact V6 source descriptor required')
    for reference in refs(descriptor):
        if row(ROOT/reference['path'])['sha256']!=reference['sha256']:raise ValueError('Original descriptor input changed: '+reference['path'])
    data=prefab_path.read_bytes();newline=b'\r\n' if b'\r\n' in data else b'\n'
    name=b'  m_Name: RB_Golden_Ash_V6'+newline
    component=b'  m_EditorClassIdentifier: RacingBois.Client.Presentation::RacingBois.Client.Presentation.RiderAnimationSet'+newline
    if data.count(name)!=1 or data.count(component)!=1 or b'fallenRootOffset:' in data:raise ValueError('Original prefab is not the unmodified legacy metadata fixture')
    changed=data.replace(name,b'  m_Name: '+CANDIDATE_ID.encode()+newline).replace(component,component+b'  fallenRootOffset: 0'+newline)
    descriptor['purpose']='Metadata-only V6 ground-origin candidate. Original art/animation bytes remain bound; mid-fall penetration about 0.153m is still open. No art or visual acceptance.'
    descriptor['assets'][0]['id']=CANDIDATE_ID;descriptor['assets'][0]['fallenRootOffset']=0
    output.mkdir(parents=True,exist_ok=True)
    candidate_descriptor=output/'descriptor.json';candidate_prefab=output/(CANDIDATE_ID+'.prefab')
    write_fresh(candidate_descriptor,(json.dumps(descriptor,indent=2)+'\n').encode())
    write_fresh(candidate_prefab,changed)
    if original!=[row(descriptor_path),row(prefab_path)]:raise ValueError('Original source changed while staging')
    manifest={'schema':1,'originalInputs':original,'candidateDescriptor':row(candidate_descriptor),'candidatePrefab':row(candidate_prefab),
              'targetPrefab':'Assets/RacingBois/Golden/Generated/Prefabs/'+CANDIDATE_ID+'.prefab',
              'legacyFallenRootOffset':-.55,'candidateFallenRootOffset':0,'metadataOnly':True,'installed':False,
              'installation':'Root may copy only this prefab to its fresh target and refresh Unity. Full Golden Import with the same original FBX would remap its materials; avoid that for this metadata-only candidate.',
              'remainingGap':'Authored clip still has about 0.153m mid-fall ground penetration at zero root; no continuous mesh baking, collision or authority changes.',
              'visualAccepted':False}
    write_fresh(output/'staged.json',(json.dumps(manifest,indent=2)+'\n').encode())
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
