"""Read-only source/art inventory snapshot. Writes only this audit's report files."""
from pathlib import Path
import collections,csv,datetime as dt,hashlib,json,re
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
cache={}
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def digest(path):
    p=Path(path);p=p if p.is_absolute() else ROOT/p
    if not p.is_file():return None
    if str(p) not in cache:
        with p.open('rb') as f:cache[str(p)]=hashlib.file_digest(f,'sha256').hexdigest()
    return cache[str(p)]
ledger=load('docs/p08/content/ContentParityLedger.json');families=load('docs/p01/assets/content_reference_ledger.json')
raw=load('docs/reverse-engineering/assets/families.json');exports=load('docs/p08/art/export-manifest.json')
bindings={}
for asset in ledger['production_assets']:
    for key in ['production_paths','authoring_paths','concept_paths','provenance_paths','qa_paths']:
        for row in asset.get(key,[]):
            if isinstance(row,dict):bindings[row['path']]=row['sha256']
for row in ledger['inputs']:bindings[row['path']]=row['sha256']
ledger_mismatch=[{'path':path,'expected':sha,'actual':digest(path)} for path,sha in sorted(bindings.items()) if digest(path)!=sha]
export_checks=[]
for asset in exports['assets']:
    for kind in ['source','fbx','concept']:
        path=asset[kind];expected=asset.get(kind+'Sha256');actual=digest(path)
        export_checks.append({'id':asset['name'],'kind':kind,'path':path,'expected':expected,'actual':actual,'matches':expected==actual})
descriptors=['docs/p08/golden/apex/v8/r2/descriptor.json','docs/p08/golden/apex/r3/descriptor.json','docs/p08/golden/ash/v3/descriptor-bind.json','docs/p08/golden/canyon/v16/descriptor.json','docs/p08/golden/garage/v5/descriptor.json']
def file_rows(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):yield value
        for item in value.values():yield from file_rows(item)
    elif isinstance(value,list):
        for item in value:yield from file_rows(item)
golden=[]
for path in descriptors:
    doc=load(path);rows={r['path']:r['sha256'] for r in file_rows(doc)}
    matches=[]
    for p in (ROOT/'docs/p08/golden/unity').glob('import-*.json'):
        d=json.loads(p.read_text(encoding='utf-8-sig'))
        bound_path=d.get('descriptor');equivalent=False
        if bound_path and d.get('descriptorSha256')==digest(bound_path):
            bound=load(bound_path)
            equivalent=all(asset in bound.get('assets',[]) for asset in doc['assets'])
        if equivalent:
            matches.append({'path':p.relative_to(ROOT).as_posix(),'descriptor':bound_path,'exactAssetEntryMatches':True,'utc':d.get('utc'),'passed':d.get('passed'),'sourceBindingPassed':d.get('sourceBindingPassed'),'sourceFingerprint':d.get('sourceFingerprint'),'scope':d.get('scope')})
    golden.append({'descriptor':path,'descriptorSha256':digest(path),'ids':[a['id'] for a in doc['assets']],
        'inputs':len(rows),'inputMismatches':[{'path':p,'expected':s,'actual':digest(p)} for p,s in rows.items() if digest(p)!=s],
        'latestMatchingImport':max(matches,key=lambda r:r.get('utc') or '') if matches else None,
        'visualAcceptance':'not accepted; see corresponding version README and matched-view review, technical receipts alone are insufficient'})
original_root=Path('C:/Users/Liquid/Downloads/Unity/racing_bois_mod');original_bad=[]
for row in ledger['reference_source_files']:
    p=original_root/row['path']
    if not p.is_file() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:original_bad.append(row['path'])
group_counts=collections.Counter(e['category'] for e in ledger['entries'])
state_counts=collections.Counter(e['status'] for e in ledger['entries'])
nonempty=[f for f in raw if f['compression']==1]
refs=load('docs/p01/assets/course_family_references.json')
rrsm_union=sorted({r['family_id_when_state1'] for r in refs if r.get('operation_state')==1 and r.get('family_id_when_state1') is not None})
images=[e for e in ledger['entries'] if e['category']=='image_catalog']
media=load('docs/p08/media/audio-manifest.json')
out={
 'schema':1,'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
 'scope':'Read-only audit snapshot. Original research retained outside production. No editor/DCC/server call or running-probe source mutation. Report is not asset acceptance.',
 'ledgerSha256':digest('docs/p08/content/ContentParityLedger.json'),'ledgerRows':len(ledger['entries']),'ledgerCategoryCounts':dict(group_counts),'ledgerStates':dict(state_counts),
 'ledgerBoundFilesChecked':len(bindings),'ledgerBindingMismatches':ledger_mismatch,
 'originalFiles':len(ledger['reference_source_files']),'originalBytes':sum(r['bytes'] for r in ledger['reference_source_files']),
 'originalHashMismatches':original_bad,'originalUniqueFileHashes':len({r['sha256'] for r in ledger['reference_source_files']}),
 'familyAccounting':{'containerEntries':len(raw),'nonemptyCompounds':len(nonempty),'nonemptyUniqueRawHashes':len({r['sha256_raw'] for r in nonempty}),
    'rrsmEventRecords':len(refs),'rrsmReferencedFamilyUnion':rrsm_union,'rrsmReferencedUniqueCount':len(rrsm_union),
    'courseMembershipCount':dict(collections.Counter(c for r in families for c in r['course_references'].split(';') if c)),
    'noCourseReference':[r['reference_id'] for r in families if not r['course_references']],
    'semanticIndependence':'Unresolved: unique compound bytes do not imply unique visual families; repeated component/LOD/frame representations must be mapped.'},
 'imageAccounting':{'referenceRows':len(images),'groups':dict(collections.Counter('/'.join(e['reference_files'][0].split('/')[:-1]) for e in images)),
    'note':'Bike/portrait/showroom images overlap other functional rows. Do not add119image rows to15SKU/8identity totals.'},
 'legacyExports':{'declared':len(exports['assets']),'kindCounts':dict(collections.Counter(a['kind'] for a in exports['assets'])),
    'hashChecks':export_checks,'mismatchingRows':sum(not r['matches'] for r in export_checks),'uniqueMismatchingPaths':sorted({r['path'] for r in export_checks if not r['matches']}),
    'bikeFbxIndices':[i for i in range(15) if (ROOT/f'Assets/RacingBois/Art/P08/RB_P08_Bike_{i:02d}.fbx').exists()],
    'bikePrefabIndices':[i for i in range(15) if (ROOT/f'Assets/RacingBois/Prefabs/P08/RB_P08_Bike_{i:02d}.prefab').exists()],
    'riderFbxIndices':[i for i in range(8) if (ROOT/f'Assets/RacingBois/Art/P08/RB_P08_Rider_{i:02d}.fbx').exists()],
    'portraitPngCount':len(list((ROOT/'Assets/RacingBois/Art/P08/Portraits').glob('*.png')))},
 'goldenCandidates':golden,
 'concepts':{'p08Bike':len(list((ROOT/'ArtSource/Concepts/P08/Bikes').glob('*.png'))),'p08Rider':len(list((ROOT/'ArtSource/Concepts/P08/Riders').glob('*.png'))),'p08Environment':len(list((ROOT/'ArtSource/Concepts/P08/Environments').glob('*.png'))),'p08UiV1':len(list((ROOT/'ArtSource/Concepts/P08/UI').glob('*.png')))},
 'media':{'runtimeOggFiles':len(list((ROOT/'Assets/RacingBois/Art/P08/Audio').rglob('*.ogg'))),'declaredClips':len(media['clips']),'clipCategoryCounts':dict(collections.Counter(c['category'] for c in media['clips']))},
 'productionPackLocations':{p:(ROOT/p).exists() for p in ['Assets/RacingBois/Content/P08','Assets/StreamingAssets/Content','Build/Content-editor','Build/Content-desktop','Build/Content','Build/Desktop-P08']},
 'availabilityMasks':dict(re.findall(r'public const int (Available\w+Mask) = (\d+);',(ROOT/'Packages/com.racingbois.foundation/Runtime/Definitions/ProductionContent.cs').read_text())),
 'protectedClubSha256':digest('ArtSource/Weapons/RB_Club.blend'),
 'globalCompletionPercentage':None}
(OUT/'snapshot.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
with (OUT/'unresolved-reference-rows.csv').open('w',encoding='utf8',newline='') as f:
    writer=csv.writer(f);writer.writerow(['id','category','label','reference_unit','semantic_independence_verified','ledger_status','replacement_ids','reference_files','remaining_work'])
    for e in ledger['entries']:writer.writerow([e['id'],e['category'],e['label'],e['reference_unit'],e['semantic_independence_verified'],e['status'],';'.join(e['replacement_ids']),';'.join(e['reference_files']),e['remaining_work']])
print(json.dumps({'originalFiles':out['originalFiles'],'originalChanged':len(original_bad),'ledgerStates':dict(state_counts),'ledgerBindingMismatches':len(ledger_mismatch),'legacyExportMismatchingRows':out['legacyExports']['mismatchingRows'],'legacyExportUniqueBadPaths':len(out['legacyExports']['uniqueMismatchingPaths']),'rrsmReferencedUniqueCount':len(rrsm_union),'goldenInputMismatches':[(g['ids'],len(g['inputMismatches'])) for g in golden],'packLocations':out['productionPackLocations']}))
