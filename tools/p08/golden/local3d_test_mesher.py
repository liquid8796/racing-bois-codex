"""CPU-only asymmetric coordinate, topology and winding test for the local mesher adapter."""
from pathlib import Path
import os,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[3]
TRIAL=ROOT/'_local/p08-local3d'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['HF_HUB_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
sys.path.insert(0,str(TRIAL/'source/TripoSR-107cefdc244c39106fa830359024f6a2f1c78871'))
import numpy as np
import torch
import trimesh
from tsr.models.isosurface import MarchingCubeHelper

resolution=65
center=np.array([.24,.55,.72]);radii=np.array([.11,.18,.08])
grid=np.stack(np.meshgrid(*[np.linspace(0,1,resolution)]*3,indexing='ij'),axis=-1)
density=1-np.sum(((grid-center)/radii)**2,axis=-1)
helper=MarchingCubeHelper(resolution)
vertices,faces=helper(torch.from_numpy((-density).astype(np.float32)).reshape(-1))
mesh=trimesh.Trimesh(vertices=vertices.numpy(),faces=faces.numpy(),process=False)
expected=np.stack([center-radii,center+radii])
bound_error=float(np.max(np.abs(mesh.bounds-expected)))
center_error=float(np.max(np.abs(mesh.center_mass-center)))
assert bound_error<1.5/(resolution-1),('axis/bounds',mesh.bounds,expected)
assert center_error<.01,('asymmetric centre',mesh.center_mass)
assert mesh.is_watertight and mesh.is_winding_consistent,'topology/winding inconsistency'
assert mesh.volume>0,('inward winding',mesh.volume)
assert np.isfinite(mesh.vertices).all() and (mesh.area_faces>0).all()
report={'passed':True,'scope':'CPU mesher adapter only; no model inference or visual acceptance.','torchVersion':torch.__version__,'resolution':resolution,'vertices':len(vertices),'faces':len(faces),'boundsError':bound_error,'centerError':center_error,'signedVolume':float(mesh.volume),'watertight':bool(mesh.is_watertight),'windingConsistent':bool(mesh.is_winding_consistent),'adapterSha256':hashlib.sha256((TRIAL/'source/TripoSR-107cefdc244c39106fa830359024f6a2f1c78871/tsr/models/cpu_marching.py').read_bytes()).hexdigest()}
(TRIAL/'evidence/mesher-test.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
