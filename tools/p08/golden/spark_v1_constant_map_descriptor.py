"""Declare the 22 existing Spark constant maps; preserve the historical descriptor and every image byte."""
from pathlib import Path
import copy
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
FOLDER=ROOT/'docs/p08/golden/spark/v1'
ROLES=['baseColor','normal','metallicSmoothness','occlusion','emission']

def sha(data):return hashlib.sha256(data).hexdigest()
def row(path):
    data=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':sha(data),'bytes':len(data)}

def main():
    target=FOLDER/'descriptor.json';historical=FOLDER/'descriptor-before-constant-maps.json'
    declarations_path=FOLDER/'constant-map-declarations.json'
    previous=historical.read_bytes() if historical.exists() else target.read_bytes()
    baseline=json.loads(previous);updated=copy.deepcopy(baseline)
    materials={material['sourceName']:material for asset in updated['assets'] for material in asset['materials']}
    if any('constantMaps' in material for material in materials.values()):raise ValueError('Historical descriptor already declares constants')
    declarations=json.loads(declarations_path.read_text())['maps']
    if len(declarations)!=22:raise ValueError('Expected the reviewed 22-map declaration set')
    seen=set();bound=[]
    for declaration in declarations:
        material=materials[declaration['material']];role=declaration['role'];identity=(declaration['material'],role)
        if identity in seen or role not in ROLES:raise ValueError('Duplicate or unknown constant map')
        seen.add(identity)
        if declaration['dimensions']!=[4,4] or not declaration['allPixelsIdentical']:raise ValueError('Declaration is not a 4x4 constant')
        source=(ROOT/declaration['input']['path']).resolve()
        if not source.is_relative_to(ROOT) or sha(source.read_bytes())!=declaration['input']['sha256']:raise ValueError('Constant source bytes changed')
        field=material[role]
        if field['path']!=declaration['destination'] or field['sha256']!=declaration['input']['sha256']:raise ValueError('Descriptor field differs from declared source')
        material.setdefault('constantMaps',[]).append(role)
        bound.append({'material':material['sourceName'],'role':role,**field})
    for material in materials.values():
        if 'constantMaps' in material:material['constantMaps'].sort(key=ROLES.index)
    candidate=(json.dumps(updated,indent=2)+'\n').encode()
    if target.read_bytes() not in [previous,candidate]:raise ValueError('Current descriptor has unrelated changes')
    if not historical.exists():historical.write_bytes(previous)
    target.write_bytes(candidate)
    receipt={'schema':1,'historicalDescriptor':row(historical),'declarations':row(declarations_path),'descriptor':row(target),
             'constantMapCount':len(bound),'maps':bound,'imageBytesChanged':False,'copiedIntoAssets':False,
             'contract':'Explicit role opt-in; actual hash-bound 4x4 8-bit RGB/RGBA PNG decoded by Unity with all pixels identical. Ordinary textures still require at least 256x256.',
             'limitations':'Clearcoat and transmission differences remain open. This enables technical preview only; no material or concept fidelity acceptance.',
             'visualAccepted':False}
    (FOLDER/'constant-map-descriptor-update.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({key:value for key,value in receipt.items() if key!='maps'},indent=2))

if __name__=='__main__':main()
