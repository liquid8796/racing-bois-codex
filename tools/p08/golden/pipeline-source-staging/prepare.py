"""Stage the explicit Golden pipeline source follow-up; preserves the earlier build handoff."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
SOURCE = ROOT / 'Assets/RacingBois/Editor/GoldenSampleBuilder.Lighting.cs'
DESKTOP = ROOT / 'Assets/RacingBois/Settings/Desktop/DesktopPipeline.asset'
original = SOURCE.read_bytes()
text = original.decode('utf-8-sig')
old = '''            var source = GraphicsSettings.currentRenderPipeline;
            Require(source != null, "A current URP pipeline is required for the review.");'''
new = '''            const string sourcePath = UrpProfileAuthoring.DesktopPipelinePath;
            ProjectPath(sourcePath, false);
            var source = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(sourcePath);
            Require(source != null && AssetDatabase.GetAssetPath(source) == sourcePath,
                "The explicit reviewed desktop URP asset is required: " + sourcePath);
            Require(!EditorUtility.IsDirty(source), "The reviewed desktop pipeline has unsaved changes.");'''
anchor = '            var pipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(path);'
if text.count(old) != 1 or text.count(anchor) != 1 or not DESKTOP.is_file():
    raise ValueError('Expected native source shape or explicit DesktopPipeline asset missing')
text = text.replace(old, new).replace(anchor, anchor + '\n            Require(pipeline != source && path != sourcePath, "Review pipeline must not overwrite its desktop source.");')
target = HERE / SOURCE.name
if target.exists() or (HERE / 'handoff.json').exists():
    raise ValueError('Preserve prior follow-up; do not overwrite a staged review')
target.write_text(text, encoding='utf-8', newline='')
sha = lambda data: hashlib.sha256(data).hexdigest()
receipt = {'schema': 1, 'source': SOURCE.relative_to(ROOT).as_posix(), 'originalSha256': sha(original),
           'candidate': target.relative_to(ROOT).as_posix(), 'candidateSha256': sha(target.read_bytes()),
           'metaSha256': sha(Path(str(SOURCE) + '.meta').read_bytes()),
           'explicitDesktopSource': DESKTOP.relative_to(ROOT).as_posix(), 'desktopSourceSha256': sha(DESKTOP.read_bytes()),
           'scope': 'Explicit source selection only; preserves old scoped-build handoff and all concept/assets. Native validation required.'}
(HERE / 'handoff.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt, indent=2))
