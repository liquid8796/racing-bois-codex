"""Apply a small auditable local-only adapter to the pinned official TripoSR source."""
from pathlib import Path
import hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[3]
TRIAL=ROOT/'_local/p08-local3d'
SRC=TRIAL/'source/TripoSR-107cefdc244c39106fa830359024f6a2f1c78871'
changes=[]
def replace(relative,old,new):
    path=SRC/relative;data=path.read_text();before=hashlib.sha256(path.read_bytes()).hexdigest()
    if new in data:return
    assert data.count(old)==1,(relative,'unexpected pinned source')
    path.write_text(data.replace(old,new),encoding='utf8')
    changes.append({'path':relative,'beforeSha256':before,'afterSha256':hashlib.sha256(path.read_bytes()).hexdigest()})
replace('tsr/system.py','torch.load(weight_path, map_location="cpu")','torch.load(weight_path, map_location="cpu", weights_only=True)')
replace('tsr/utils.py','import rembg','# Racing Bois local trial: supplied alpha is mandatory; no background model/service.\nrembg = None')
replace('tsr/models/isosurface.py','from torchmcubes import marching_cubes','from .cpu_marching import marching_cubes  # reviewed local CPU adapter')
replace('tsr/models/tokenizers/image.py','from dataclasses import dataclass','from dataclasses import dataclass\nimport os')
old='''hf_hub_download(
                    repo_id=self.cfg.pretrained_model_name_or_path,
                    filename="config.json",
                )'''
replace('tsr/models/tokenizers/image.py',old,'os.environ["RACING_BOIS_DINO_CONFIG"]  # task-local pinned config; no runtime network')
adapter=SRC/'tsr/models/cpu_marching.py'
adapter.write_text('''"""Racing Bois local trial: CPU Lewiner extraction, preserving TripoSR's axis convention."""
import numpy as np
import torch
from skimage.measure import marching_cubes as extract_surface

def marching_cubes(volume, isovalue):
    values=np.ascontiguousarray(volume.detach().cpu().numpy(),dtype=np.float32)
    vertices,faces,_,_=extract_surface(values,level=float(isovalue),gradient_direction="ascent",allow_degenerate=False)
    # The existing TripoSR helper swaps z/x afterward, as it does for torchmcubes.
    return torch.from_numpy(vertices[:,[2,1,0]].copy()),torch.from_numpy(faces.astype(np.int64,copy=True))
''')
changes.append({'path':'tsr/models/cpu_marching.py','afterSha256':hashlib.sha256(adapter.read_bytes()).hexdigest()})
info=json.load(urllib.request.urlopen('https://huggingface.co/api/models/facebook/dino-vitb16',timeout=25))
url='https://huggingface.co/facebook/dino-vitb16/resolve/'+info['sha']+'/config.json'
data=urllib.request.urlopen(url,timeout=25).read()
config=TRIAL/'models/dino-vitb16/config.json';config.parent.mkdir(parents=True,exist_ok=True);config.write_bytes(data)
receipt={'sourceCommit':'107cefdc244c39106fa830359024f6a2f1c78871','patches':changes,'dinoConfig':{'revision':info['sha'],'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},'scope':'Only isolated trial source modified. No Blender addon, global package or game source changes.'}
(TRIAL/'evidence/source-patches.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('LOCAL3D_PATCHES_READY',len(changes),'DINO config bytes',len(data))
