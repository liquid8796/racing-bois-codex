"""Real isolated file tests for immutable publishing, not Unity/visual acceptance."""
from pathlib import Path
import hashlib,json,uuid
from unittest.mock import patch
import publish_verified as publisher

AREA=publisher.PROJECT/'_local/p08-ash-v6-publisher-tests'/uuid.uuid4().hex
AREA.mkdir(parents=True)
results=[]
def put(root,path,data):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    return {'path':path,'sha256':hashlib.sha256(data).hexdigest()}
def fixture(name):
    root=(AREA/name).resolve();root.mkdir()
    source=put(root,'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',b'source unchanged')
    fbx=put(root,'_local/p08-ash-v6-staging/RB_Golden_Ash_V6.fbx',b'fbx bytes')
    texture=[put(root,f'ArtSource/P08/Golden/Ash/V6/Textures/AshV6_{role}_{channel}.png',(role+channel).encode()) for role in publisher.ROLES for channel in publisher.CHANNELS]
    original=put(root,'ArtSource/Weapons/RB_Club.blend',b'protected original')
    delivery={'source':source,'fbx':fbx,'newTextures':texture,'originalsPreserved':[original],'visualAccepted':False,'nativeUnityVerified':False}
    descriptor={'assets':[{'source':source,'fbx':fbx,'materials':[{'baseColor':v} for v in texture],'clips':[dict(fbx,name='RB_Ride')]}]}
    d=put(root,str(publisher.DOC/'delivery.json'),json.dumps(delivery).encode())
    s=put(root,str(publisher.DOC/'descriptor-staged.json'),json.dumps(descriptor).encode())
    return root,publisher.Pins(d['sha256'],s['sha256']),delivery
def run(name,action):
    try:action();results.append({'name':name,'passed':True})
    except Exception as e:results.append({'name':name,'passed':False,'error':str(e)})
def require_error(action,code):
    try:action()
    except publisher.PublishError as e:
        assert code in str(e),(code,str(e));return
    raise AssertionError('Expected failure: '+code)
def first_and_repeat():
    root,pins,data=fixture('idempotent');before={r['path']:(root/r['path']).read_bytes() for r in publisher.references(data)}
    first=publisher.publish(root,pins);assert first['createdAssetFiles']==17 and first['descriptorCreated']
    meta=root/str(publisher.DEST/'Textures.meta');meta.write_bytes(b'keep Unity metadata')
    old_times={p:p.stat().st_mtime_ns for p in (root/str(publisher.DEST)).rglob('*') if p.is_file()}
    second=publisher.publish(root,pins);assert second['createdAssetFiles']==0 and not second['descriptorCreated'] and second['reusedAssetFiles']==17
    assert all(p.stat().st_mtime_ns==t for p,t in old_times.items())
    assert all((root/path).read_bytes()==value for path,value in before.items())
    bound=json.loads((root/str(publisher.DOC/'descriptor.json')).read_text())
    assert bound['assets'][0]['fbx']['path'].startswith(str(publisher.DEST))
def dry_run():
    root,pins,data=fixture('dry');r=publisher.publish(root,pins,True);assert r['plannedAssetFiles']==17 and not (root/str(publisher.DEST)).exists()
def conflict():
    root,pins,data=fixture('conflict');target=root/str(publisher.DEST/'RB_Golden_Ash_V6.fbx');target.parent.mkdir(parents=True);target.write_bytes(b'foreign')
    require_error(lambda:publisher.publish(root,pins),'destination_hash_conflict');assert target.read_bytes()==b'foreign' and not (target.parent/'Textures').exists()
def source_tamper():
    root,pins,data=fixture('tamper');(root/data['newTextures'][-1]['path']).write_bytes(b'changed')
    require_error(lambda:publisher.publish(root,pins),'input_hash_mismatch');assert not (root/str(publisher.DEST)).exists()
def metadata_tamper():
    root,pins,data=fixture('metadata');(root/str(publisher.DOC/'descriptor-staged.json')).write_bytes(b'{}')
    require_error(lambda:publisher.publish(root,pins),'frozen_manifest_changed');assert not (root/str(publisher.DEST)).exists()
def changed_while_copying():
    root,pins,data=fixture('copy_race');copy=publisher.shutil.copyfile
    def interrupted(source,target):
        Path(source).write_bytes(b'changed after preflight');return copy(source,target)
    with patch.object(publisher.shutil,'copyfile',interrupted):require_error(lambda:publisher.publish(root,pins),'source_changed_before_publish')
    assert not (root/str(publisher.DEST/'RB_Golden_Ash_V6.fbx')).exists()
def descriptor_conflict():
    root,pins,data=fixture('descriptor');(root/str(publisher.DOC/'descriptor.json')).write_bytes(b'user edits')
    require_error(lambda:publisher.publish(root,pins),'existing_descriptor_conflict');assert not (root/str(publisher.DEST)).exists()
for name,action in [('first_publish_and_exact_idempotent_retry',first_and_repeat),('read_only_preflight',dry_run),('destination_conflict_before_mutation',conflict),
    ('last_input_tamper_before_any_copy',source_tamper),('pinned_metadata_tamper',metadata_tamper),('source_changed_during_copy_not_published',changed_while_copying),('descriptor_conflict_before_any_copy',descriptor_conflict)]:run(name,action)
report={'passed':all(r['passed'] for r in results),'tests':len(results),'results':results,'fixtureDirectory':AREA.relative_to(publisher.PROJECT).as_posix(),'scope':'Isolated real file IO; no Unity or image/render claims.'}
(publisher.PROJECT/'docs/p08/golden/ash/v6/publisher-tests.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
