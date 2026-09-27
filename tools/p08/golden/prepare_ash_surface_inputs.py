"""Convert only CC0 static eye/brow asset data for safe-mode OBJ import."""
from pathlib import Path
from zipfile import ZipFile
import hashlib,json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'ArtSource/P08/Golden/Ash/AnatomyV1'
archive=ROOT/'_local/mpfb-data/makehuman_system_assets_cc0.zip'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive_hash=sha(archive)
base=[list(map(float,l.split()[1:4])) for l in (OUT/'RB_Ash_AnatomicalBase.obj').read_text().splitlines() if l.startswith('v ')]
target=OUT/'ReferenceSurfaces'
target.mkdir(exist_ok=True)
inventory=[]
with ZipFile(archive) as z:
    for name in [
        'skins/young_caucasian_male/young_lightskinned_male_diffuse.png',
        'skins/young_caucasian_male/young_caucasian_male.mhmat',
        'eyes/materials/brown_eye.png','eyes/materials/brown.mhmat',
        'eyes/low-poly/low-poly.obj','eyes/low-poly/low-poly.mhclo',
        'eyebrows/eyebrow001/eyebrow001.obj','eyebrows/eyebrow001/eyebrow001.mhclo',
        'eyebrows/eyebrow001/eyebrow001.png','eyebrows/eyebrow001/eyebrow001.mhmat',
    ]:
        destination=target/Path(name).name
        destination.write_bytes(z.read(name))
        inventory.append({'archive_path':name,'sha256':sha(destination),'license':'CC0-1.0'})
    for name,stem in [('eyes/low-poly/low-poly','Eyes'),('eyebrows/eyebrow001/eyebrow001','Brows')]:
        mhclo=z.read(name+'.mhclo').decode('utf-8').splitlines()
        factors=[1,1,1]
        rows=[];active=False
        for line in mhclo:
            values=line.split()
            if not values or line.startswith('#'):continue
            if values[0] in ('x_scale','y_scale','z_scale'):
                axis={'x_scale':0,'y_scale':1,'z_scale':2}[values[0]]
                a,b=int(values[1]),int(values[2]);factors[axis]=abs(base[a][axis]-base[b][axis])/float(values[3])
            elif values[0]=='verts':active=True
            elif active and len(values)==1 and values[0].isdigit():rows.append(base[int(values[0])])
            elif active and len(values)==9:
                indices=list(map(int,values[:3]));weights=list(map(float,values[3:6]));offset=list(map(float,values[6:]))
                rows.append([sum(base[i][axis]*weight for i,weight in zip(indices,weights))+offset[axis]*factors[axis] for axis in range(3)])
        original=z.read(name+'.obj').decode('utf-8').splitlines()
        assert len(rows)==sum(1 for l in original if l.startswith('v '))
        output=['# CC0 MakeHuman dataset fitted by numeric data, see surface-provenance.json.']
        output += [f'v {p[0]:.9f} {p[1]:.9f} {p[2]:.9f}' for p in rows]
        output += [l for l in original if l.startswith(('vt ','f '))]
        destination=OUT/f'RB_Ash_Anatomy_{stem}.obj'
        destination.write_text('\n'.join(output)+'\n')
        inventory.append({'fitted_output':destination.name,'sha256':sha(destination),'vertices':len(rows)})
(OUT/'surface-provenance.json').write_text(json.dumps({
 'archive_url':'https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip',
 'archive_sha256':archive_hash,'asset_license':'CC0-1.0',
 'official_license_listing':'https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html',
 'input_assets':inventory,'addon_code_executed':False,
 'status':'anatomical-reference-data-not-final-Ash-materials'},indent=2)+'\n')
print(json.dumps({'archive_sha256':archive_hash,'data_assets':len(inventory),'status':'staged'}))
