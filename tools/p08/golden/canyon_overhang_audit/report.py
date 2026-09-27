"""Create geometry evidence plots/summary from the actual read-only Blender receipt."""
from __future__ import annotations
import copy
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[4]
DOC=ROOT/'docs/p08/golden/canyon/v17/overhang-audit'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=DOC,help='Use a fresh output directory when reproducing frozen plots.')
OUTPUT=parser.parse_args().output.resolve()
OUTPUT.mkdir(parents=True,exist_ok=True)
if any((OUTPUT/name).exists() for name in ['side-profile-provenance.png','side-profile-provenance.svg','summary.json']):
    raise RuntimeError('Preserve existing diagnostic outputs; pass --output with a fresh directory.')
raw_path=DOC/'frozen-mesh-comparison.json'
archive=DOC/'frozen-mesh-comparison.json.gz'
raw=raw_path.read_bytes() if raw_path.exists() else gzip.decompress(archive.read_bytes())
receipt=json.loads(raw)
data=json.loads(receipt['result']['structuredContent']['result'].split('CANYON_OVERHANG_CAUSAL_AUDIT ',1)[1])
if not archive.exists():
    archive.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
if gzip.decompress(archive.read_bytes())!=raw:raise RuntimeError('Raw evidence archive verification failed.')
by_version={version['version']:{row['object']:row for row in version['objects']} for version in data['versions']}
scans={scan['slug']:scan['mesh'] for scan in data['originalScans']}

fig,axes=plt.subplots(2,4,figsize=(17,9),layout='constrained')
for row_index,(name,slug) in enumerate([('Canyon_L0_Far_33','namaqualand_cliff_02'),('Canyon_L0_Far_34','namaqualand_cliff_01')]):
    groups=[scans[slug],by_version['V13'][name],by_version['V14'][name],by_version['V17-05'][name]]
    labels=['Original CC0 scan','V13: scaled and cap-compressed','V14 open / V15 closed','Frozen V17 candidate05']
    for column,(mesh,title) in enumerate(zip(groups,labels)):
        points=mesh['worldVertices'];low=mesh['minimumBlender']
        axis=axes[row_index,column]
        axis.scatter([p[1]-low[1] for p in points],[p[2]-low[2] for p in points],s=.4 if column==0 else 1.2,
                     color='#245a88',alpha=.38 if column==0 else .62,rasterized=True,label='Open/source vertices' if column==2 else None)
        if column==2:
            closed=by_version['V15'][name]['worldVertices']
            axis.scatter([p[1]-low[1] for p in closed],[p[2]-low[2] for p in closed],s=1,
                         color='#d07935',alpha=.4,rasterized=True,label='Closed vertices')
            axis.legend(fontsize=7,loc='lower right')
        axis.set_aspect('equal',adjustable='box')
        axis.set_title(title,fontsize=10)
        axis.set_xlabel('Depth Y (m), translated origin',fontsize=8)
        axis.set_ylabel('Height Z (m)',fontsize=8)
        axis.grid(alpha=.18);axis.tick_params(labelsize=8)
        axis.text(.02,.98,name.replace('Canyon_L0_','')+'\n'+slug,transform=axis.transAxes,va='top',fontsize=7,
                  bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'})
fig.suptitle('Canyon overhang provenance — actual mesh vertices, side projection',fontsize=15)
fig.supxlabel('Each panel uses metres and equal axis scale; only its origin is translated. No material or lighting inference, and no visual acceptance.',fontsize=9)
fig.savefig(OUTPUT/'side-profile-provenance.png',dpi=150)
fig.savefig(OUTPUT/'side-profile-provenance.svg')
plt.close(fig)

summary=copy.deepcopy(data)
for version in summary['versions']:
    for mesh in version['objects']:mesh.pop('worldVertices',None)
for scan in summary['originalScans']:scan['mesh'].pop('worldVertices',None)
summary['rawReceipt']={'path':archive.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
    'encoding':'gzip of exact MCP JSON receipt','uncompressedSha256':hashlib.sha256(raw).hexdigest(),'uncompressedBytes':len(raw)}
summary['facts']={
 'maximumV13ToV14VertexSetChangeMetres':max(item['v13ToV14NearestMetres']['maximum'] for item in data['comparisons']),
 'maximumV14ToV15ClosureVertexSetChangeMetres':max(item['v14ToV15ClosureNearestMetres']['maximum'] for item in data['comparisons']),
 'maximumV15ToV16NormalizationVertexSetChangeMetres':max(item['v15ToV16NormalizationNearestMetres']['maximum'] for item in data['comparisons']),
 'maximumV16ToV17AffineFitErrorMetres':max(item['v16ToV17MaximumAffineFitResidualMetres'] for item in data['comparisons']),
 'maximumV17ClosedToTransformedOpenDistanceMetres':max(item['v17ClosedToTransformedV14OpenNearestMetres']['maximum'] for item in data['comparisons'])}
summary['causalInterpretation']='Large shape/proportion changes predate closure and are amplified by V17 affine scaling. V15 adds a bounded thin shell and can expose backing/rim faces. Camera rays prove the first visible Far33 face uses added Canyon_Sandstone, while neighboring Far34/35 hits use original scan materials. Both profile authoring and visible backing require correction; changing color alone does not fix the geometry.'
(OUTPUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'facts':summary['facts'],'archivedReceipt':summary['rawReceipt'],
                  'summaryBytes':(OUTPUT/'summary.json').stat().st_size},indent=2))
