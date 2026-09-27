"""One authorized offline TripoSR shape trial; bounded GPU allocator and preserved source alpha."""
from pathlib import Path
import os,sys,json,time,hashlib,traceback
ROOT=Path(__file__).resolve().parents[3]
TRIAL=ROOT/'_local/p08-local3d'
OUTPUT=TRIAL/'outputs/apex-grid128';OUTPUT.mkdir(parents=True,exist_ok=True)
for key,value in {'HF_HOME':str(TRIAL/'hf-cache'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','HF_HUB_DISABLE_IMPLICIT_TOKEN':'1','DO_NOT_TRACK':'1','RACING_BOIS_DINO_CONFIG':str(TRIAL/'models/dino-vitb16/config.json')}.items():os.environ[key]=value
sys.path.insert(0,str(TRIAL/'source/TripoSR-107cefdc244c39106fa830359024f6a2f1c78871'))
import numpy as np
from PIL import Image
import torch
from tsr.system import TSR

source=ROOT/'ArtSource/Concepts/P08/Golden/apex-local3d-input-v1.png'
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash=='c8c6ce7799ea86c64b13ca33fa5f2450e636ba64579b81914d1eff6b3f93fdb4'
rgba=Image.open(source).convert('RGBA');alpha=rgba.getchannel('A');bbox=alpha.getbbox();assert bbox
crop=rgba.crop(bbox);size=512;limit=round(size*.85);ratio=min(limit/crop.width,limit/crop.height)
crop=crop.resize((round(crop.width*ratio),round(crop.height*ratio)),Image.Resampling.LANCZOS)
canvas=Image.new('RGBA',(size,size),(0,0,0,0));canvas.paste(crop,((size-crop.width)//2,(size-crop.height)//2))
pixels=np.asarray(canvas).astype(np.float32)/255
composite=pixels[:,:,:3]*pixels[:,:,3:4]+.5*(1-pixels[:,:,3:4])
image=Image.fromarray(np.rint(composite*255).astype(np.uint8),'RGB')
image.save(OUTPUT/'model-input.png')
canvas.save(OUTPUT/'model-input-alpha.png')
report={'status':'running','visualAccepted':False,'source':str(source.relative_to(ROOT)),'sourceSha256':source_hash,'alphaPreserved':True,'cropBounds':bbox,'foregroundRatio':.85,'gridResolution':128,'chunkSize':2048,'torchVersion':torch.__version__,'sourceCommit':'107cefdc244c39106fa830359024f6a2f1c78871','modelCommit':'5b521936b01fbe1890f6f9baed0254ab6351c04a','networkDisabled':True}
started=time.monotonic();model=None
try:
    torch.set_num_threads(4)
    assert torch.cuda.is_available(),'CUDA unavailable; do not silently change trial device'
    torch.cuda.init();free,total=torch.cuda.mem_get_info()
    budget=min(int(4.5*1024**3),free-768*1024**2)
    assert budget>3*1024**3,'Insufficient free VRAM for this bounded trial'
    torch.cuda.set_per_process_memory_fraction(budget/total,0)
    torch.cuda.reset_peak_memory_stats()
    report.update({'freeVramBeforeBytes':free,'totalVramBytes':total,'allocatorBudgetBytes':budget,'device':torch.cuda.get_device_name(0)})
    print('LOCAL3D_GPU_TRIAL_START',json.dumps({k:report[k] for k in ['freeVramBeforeBytes','allocatorBudgetBytes','device']}),flush=True)
    marker=time.monotonic()
    model=TSR.from_pretrained(str(TRIAL/'models/TripoSR'),config_name='config.yaml',weight_name='model.ckpt')
    model.renderer.set_chunk_size(2048);model.to('cuda:0');model.eval()
    report['loadSeconds']=time.monotonic()-marker
    print('LOCAL3D_MODEL_LOADED',report['loadSeconds'],flush=True)
    marker=time.monotonic()
    with torch.no_grad():codes=model([image],device='cuda:0')
    torch.cuda.synchronize();report['inferenceSeconds']=time.monotonic()-marker
    print('LOCAL3D_INFERENCE_COMPLETE',report['inferenceSeconds'],flush=True)
    marker=time.monotonic()
    with torch.no_grad():mesh=model.extract_mesh(codes,has_vertex_color=True,resolution=128)[0]
    report['extractionSeconds']=time.monotonic()-marker
    assert len(mesh.vertices)>0 and len(mesh.faces)>0 and np.isfinite(mesh.vertices).all()
    destination=OUTPUT/'apex-grid128.glb';mesh.export(destination)
    report.update({'status':'completed_unaccepted','vertices':len(mesh.vertices),'faces':len(mesh.faces),'meshWatertight':bool(mesh.is_watertight),'meshWindingConsistent':bool(mesh.is_winding_consistent),'output':str(destination.relative_to(ROOT)),'outputSha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
except torch.cuda.OutOfMemoryError as error:
    report.update({'status':'failed_oom','error':str(error)})
except Exception as error:
    report.update({'status':'failed','error':type(error).__name__+': '+str(error),'traceback':traceback.format_exc()})
finally:
    report['elapsedSeconds']=time.monotonic()-started
    if torch.cuda.is_initialized():
        report['peakAllocatedBytes']=torch.cuda.max_memory_allocated()
        report['peakReservedBytes']=torch.cuda.max_memory_reserved()
    if model is not None:del model
    if torch.cuda.is_initialized():torch.cuda.empty_cache()
    (OUTPUT/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print('LOCAL3D_TRIAL_RESULT',json.dumps(report),flush=True)
if report['status']!='completed_unaccepted':raise SystemExit(1)
