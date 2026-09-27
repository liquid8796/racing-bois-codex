"""Negative controls mutate only in-memory copies of authored translation data."""
import copy
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

STAGE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('career_generator',STAGE/'generate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
canonical=module.read_inventory();protected=module.load(STAGE/'protected-tokens.json')
original=module.load(STAGE/'locales/ENU.json')
results=[]

def reject(name,operation):
    try: operation()
    except ValueError as error: results.append({'case':name,'rejected':True,'reason':str(error)})
    else: raise AssertionError('Invalid candidate accepted: '+name)

for name in ['missing_key','extra_key','blank_text','wrong_locale','missing_argument','extra_argument','duplicate_argument',
             'unclosed_brace','stray_brace','protected_name_changed','authored_line_break_removed']:
    candidate=copy.deepcopy(original)
    if name=='missing_key': del candidate['strings']['career.bike.preview']
    elif name=='extra_key': candidate['strings']['career.unreviewed']='Unreviewed'
    elif name=='blank_text': candidate['strings']['career.bike.preview']=' '
    elif name=='wrong_locale': candidate['locale']='VI'
    elif name=='missing_argument': candidate['strings']['career.garage.previewTooltip']='Preview'
    elif name=='extra_argument': candidate['strings']['career.garage.previewTooltip']='Preview {bike} {extra}'
    elif name=='duplicate_argument': candidate['strings']['career.garage.previewTooltip']='Preview {bike} {bike}'
    elif name=='unclosed_brace': candidate['strings']['career.garage.previewTooltip']='Preview {bike'
    elif name=='stray_brace': candidate['strings']['career.garage.previewTooltip']='Preview {bike}}'
    elif name=='protected_name_changed': candidate['strings']['career.garage.restartConfirm']=candidate['strings']['career.garage.restartConfirm'].replace('Spark 450','Other bike')
    elif name=='authored_line_break_removed': candidate['strings']['career.bike.compare']=candidate['strings']['career.bike.compare'].replace('\n',' ')
    reject(name,lambda:module.validate_locale(candidate,'ENU',canonical,protected))
candidate=module.load(STAGE/'VI.json');candidate['strings']['career.bike.preview']='Changed source'
reject('source_vi_changed',lambda:module.validate_locale(candidate,'VI',canonical,protected))
reject('duplicate_json_key',lambda:json.loads('{"key":"first","key":"second"}',object_pairs_hook=module.strict_pairs))
real_digest=module.digest
for name,target in [('canonical_drift',STAGE/'canonical-source.json'),('live_source_drift',module.ROOT/canonical['sourceFiles'][0]['path'])]:
    def changed(path):
        return '0'*64 if path==target else real_digest(path)
    with patch.object(module,'digest',side_effect=changed):
        reject(name,module.read_inventory)
receipt={'passed':True,'controls':results,'scope':'Authored-data negative controls using in-memory mutations; no source/locale files changed, no native UI or linguistic acceptance.'}
(STAGE/'generation-controls.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print('Career generation negative controls PASS:',len(results))
