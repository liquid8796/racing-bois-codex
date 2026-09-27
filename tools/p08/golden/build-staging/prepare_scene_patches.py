"""Stage owned-asset saves; never writes live Assets or calls Unity."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
CHANGES = {
    'GoldenSampleBuilder.Lighting.cs': [
        ('EditorUtility.SetDirty(pipeline);', 'EditorUtility.SetDirty(pipeline); AssetDatabase.SaveAssetIfDirty(pipeline);')],
    'GoldenSampleBuilder.Scene.cs': [
        ('AssetDatabase.SaveAssets();', 'EditorUtility.SetDirty(floorMaterial); AssetDatabase.SaveAssetIfDirty(floorMaterial);')],
    'GoldenSampleBuilder.Environment.cs': [
        ('AssetDatabase.SaveAssets();', 'EditorUtility.SetDirty(sky); AssetDatabase.SaveAssetIfDirty(sky);')],
    'GoldenSampleBuilder.Garage.cs': [
        ('AssetDatabase.SaveAssets(); Require(recipeFile.sha256 == Digest(recipePath), "Indoor recipe changed during creation.");',
         'foreach (var material in emissiveCopies.Values) AssetDatabase.SaveAssetIfDirty(material);\n                Require(recipeFile.sha256 == Digest(recipePath), "Indoor recipe changed during creation.");'),
        ('EditorSceneManager.SaveScene(scene), "Baked garage scene save failed."); AssetDatabase.SaveAssets();',
         'EditorSceneManager.SaveScene(scene), "Baked garage scene save failed.");'),
        ('Require(paths.All(p => !string.IsNullOrEmpty(p) && File.Exists(p)), "A lighting output has no saved file identity.");',
         'foreach (string ownedPath in paths.Where(p => !string.IsNullOrEmpty(p) && p.StartsWith(lightingFolder + "/", StringComparison.Ordinal)))\n                {\n                    var ownedAsset = AssetDatabase.LoadMainAssetAtPath(ownedPath);\n                    if (ownedAsset != null) AssetDatabase.SaveAssetIfDirty(ownedAsset);\n                }\n                Require(paths.All(p => !string.IsNullOrEmpty(p) && File.Exists(p)), "A lighting output has no saved file identity.");')]
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

rows = []
for name, replacements in CHANGES.items():
    source = ROOT / 'Assets/RacingBois/Editor' / name
    original = source.read_bytes()
    text = original.decode('utf-8-sig')
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError(f'Expected one exact source block in {name}: {old}')
        text = text.replace(old, new)
    if 'AssetDatabase.SaveAssets()' in text:
        raise ValueError('Global save remains: ' + name)
    target = HERE / name
    target.write_text(text, encoding='utf-8', newline='')
    rows.append({'source': source.relative_to(ROOT).as_posix(), 'sourceSha256': sha(original),
                 'staged': target.relative_to(ROOT).as_posix(), 'stagedSha256': sha(target.read_bytes())})
(HERE / 'scene-patch-inputs.json').write_text(json.dumps({'schema': 1, 'liveEdits': False, 'files': rows}, indent=2) + '\n', encoding='utf-8')
print('Staged four scene-authoring replacements; no live Assets changed.')
