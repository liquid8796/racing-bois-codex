"""Stage the narrowly scoped receipt repair without writing Assets or old evidence."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
CHANGES = {
    'GoldenSampleBuilder.Import.cs': [
        ('receipt.failure = error.GetType().Name + ": " + error.Message;',
         'receipt.passed = false; receipt.failure = error.GetType().Name + ": " + error.Message;'),
        ('File.WriteAllText(ReceiptRoot + "/" + name + "-" + receipt.attemptId + ".json", JsonUtility.ToJson(receipt, true));',
         'GoldenReceiptFiles.WriteAtomic(ReceiptRoot + "/" + name + "-" + receipt.attemptId + ".json", JsonUtility.ToJson(receipt, true));'),
        ('File.WriteAllText(ReceiptRoot + "/" + name + "-latest.json", JsonUtility.ToJson(receipt, true));',
         'GoldenReceiptFiles.WriteAtomic(ReceiptRoot + "/" + name + "-latest.json", JsonUtility.ToJson(receipt, true));')],
    'GoldenSampleBuilder.Validation.cs': [
        ('imported != null && imported.passed && imported.sourceBindingPassed && imported.sourceFingerprint == receipt.sourceFingerprint',
         'imported != null && GoldenReceiptFiles.ImportSucceeded(imported.passed, imported.sourceBindingPassed, imported.failure) && imported.sourceFingerprint == receipt.sourceFingerprint'),
        ('catch (Exception error) { receipt.failure = error.GetType().Name + ": " + error.Message;',
         'catch (Exception error) { receipt.passed = false; receipt.failure = error.GetType().Name + ": " + error.Message;')],
    'GoldenSampleBuilder.Promotion.cs': [
        ('imported != null && imported.schema == 1 && imported.passed && imported.sourceBindingPassed &&',
         'imported != null && imported.schema == 1 && GoldenReceiptFiles.ImportSucceeded(imported.passed, imported.sourceBindingPassed, imported.failure) &&')],
    'GoldenProductionGate.cs': [
        ('public string descriptor, descriptorSha256;', 'public string descriptor, descriptorSha256, failure;'),
        ('native != null && native.schema == 1 && native.passed && native.sourceBindingPassed',
         'native != null && native.schema == 1 && GoldenReceiptFiles.ImportSucceeded(native.passed, native.sourceBindingPassed, native.failure)')]
}

manifest = HERE / 'handoff.json'
if manifest.exists():
    raise ValueError('Preserve the existing staged handoff; do not rebind it silently.')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rows = []
for name, changes in CHANGES.items():
    source = ROOT / 'Assets/RacingBois/Editor' / name
    original = source.read_bytes()
    text = original.decode('utf-8-sig')
    for old, new in changes:
        if text.count(old) != 1:
            raise ValueError('Expected one exact source block: ' + name + ': ' + old)
        text = text.replace(old, new)
    target = HERE / name
    target.write_text(text, encoding='utf-8', newline='')
    meta = Path(str(source) + '.meta')
    rows.append({'source': source.relative_to(ROOT).as_posix(), 'originalSha256': hashlib.sha256(original).hexdigest(),
                 'candidate': target.relative_to(ROOT).as_posix(), 'candidateSha256': sha(target), 'metaSha256': sha(meta)})
helper = HERE / 'GoldenSampleBuilder.ReceiptFiles.cs'
rows.append({'source': 'Assets/RacingBois/Editor/' + helper.name, 'originalSha256': None,
             'candidate': helper.relative_to(ROOT).as_posix(), 'candidateSha256': sha(helper), 'metaSha256': None})
manifest.write_text(json.dumps({'schema': 1, 'liveEdits': False, 'files': rows,
                               'retainedFailure': 'docs/p08/golden/unity/import-b89d27372abd44b6a0d80e4528ec1c70.json'}, indent=2) + '\n', encoding='utf-8')
print('Staged receipt repair; live Assets and contradictory historical receipt unchanged.')
