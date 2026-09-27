"""Read-only UV-island statistics; does not edit or output either image."""
from pathlib import Path
from PIL import Image
import numpy as np
import hashlib,json
def neighbours(mask,mode):
    padded=np.pad(mask,1);out=np.ones_like(mask) if mode=='erode' else np.zeros_like(mask)
    for dy in range(3):
        for dx in range(3):
            block=padded[dy:dy+mask.shape[0],dx:dx+mask.shape[1]]
            if mode=='erode':out&=block
            else:out|=block
    return out
def boundary_distances(source,target):
    reached=source.copy();pending=target&~reached;values=[0]*int((target&reached).sum())
    for radius in range(1,129):
        if not pending.any():break
        reached=neighbours(reached,'dilate');found=pending&reached
        values.extend([radius]*int(found.sum()));pending&=~found
    if pending.any():raise RuntimeError('Boundary drift exceeds measured 128 pixel radius')
    return values
def major_components(mask):
    parent=[];sizes=[];previous=[]
    def root(label):
        while parent[label]!=label:
            parent[label]=parent[parent[label]];label=parent[label]
        return label
    for row in mask:
        diff=np.diff(np.r_[False,row,False].astype(np.int8));starts=np.flatnonzero(diff==1);ends=np.flatnonzero(diff==-1)-1;current=[]
        for start,end in zip(starts,ends):
            matches=[root(label) for left,right,label in previous if start<=right+1 and end+1>=left]
            if not matches:
                label=len(parent);parent.append(label);sizes.append(0)
            else:
                label=matches[0]
                for other in matches[1:]:
                    a,b=root(label),root(other)
                    if a!=b:parent[b]=a;sizes[a]+=sizes[b];sizes[b]=0
            label=root(label);sizes[label]+=int(end-start+1);current.append((int(start),int(end),label))
        previous=current
    return sum(parent[i]==i and size>100 for i,size in enumerate(sizes))

ROOT=Path(__file__).resolve().parents[4]
original=ROOT/'Assets/RacingBois/Art/P08/Golden/Ash/V2/Textures/AshV2_TailoredClothing_BaseColor.png'
candidate=ROOT/'ArtSource/P08/Golden/Ash/TextureCandidates/tailored-leather-v1.png'
a=np.asarray(Image.open(original).convert('RGB'));b=np.asarray(Image.open(candidate).convert('RGB'))
h,w=b.shape[:2]
# Sample the original foreground mask at the candidate pixel-center positions.
# This normalizes coordinate grids for measurement; no raster is changed/saved.
ys=np.minimum(((np.arange(h)+.5)*a.shape[0]/h).astype(int),a.shape[0]-1)
xs=np.minimum(((np.arange(w)+.5)*a.shape[1]/w).astype(int),a.shape[1]-1)
base=a[ys[:,None],xs[None,:],:]
ma=base.max(axis=2)>12;mb=b.max(axis=2)>12
edge_a=ma&~neighbours(ma,'erode');edge_b=mb&~neighbours(mb,'erode')
distances=np.array(boundary_distances(edge_a,edge_b)+boundary_distances(edge_b,edge_a))
intersection=(ma&mb).sum();union=(ma|mb).sum()
result={
 'scope':'Measured normalized-canvas UV foreground mask drift only; not a 3D fidelity or artistic similarity score.',
 'originalSize':[a.shape[1],a.shape[0]],'candidateSize':[w,h],
 'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),
 'candidateSha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
 'foregroundThresholdRgbMax':12,'intersectionOverUnion':float(intersection/union),
 'missingForegroundPixels':int((ma&~mb).sum()),'extraForegroundPixels':int((mb&~ma).sum()),
 'symmetricBoundaryDistanceCandidatePixels':{'metric':'Chebyshev on pixel grid','median':float(np.median(distances)),'p95':float(np.quantile(distances,.95)),'max':float(distances.max())},
 'majorForegroundComponentCountOriginal':major_components(ma),'majorForegroundComponentCountCandidate':major_components(mb),
 'visualFinding':'Broad pale marbling and directional-looking fold shading are excessive for a neutral albedo; colored boundary fringe is visible. Candidate remains unaccepted.',
 'imagesModified':False,
}
(ROOT/'docs/p08/golden/ash/v2/texture-candidate-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
