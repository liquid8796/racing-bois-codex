using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        /// <summary>Reuses the full native validator against an explicit immutable import, never import-latest.</summary>
        public static AssetReceipt ValidatePromotionSource(string descriptorPath, string assetId, string importReceiptPath)
        {
            var descriptor = ReadDescriptor(descriptorPath);
            ProjectPath(importReceiptPath, false);
            var imported = JsonUtility.FromJson<ImportReceipt>(File.ReadAllText(importReceiptPath));
            var before = InputSnapshot(descriptorPath, descriptor);
            Require(imported != null && imported.schema == 1 && imported.passed && imported.sourceBindingPassed &&
                imported.descriptor == descriptorPath && imported.descriptorSha256 == Digest(descriptorPath) &&
                imported.sourceFingerprint == Fingerprint(before), "Promotion requires an unchanged, source-bound native import.");
            Require(imported.outputs != null && imported.outputs.Length > 0, "Native import has no output binding.");
            foreach (var output in imported.outputs) VerifyInput(new InputFile { path = output.path, sha256 = output.sha256 });
            var spec = descriptor.assets.Single(x => x.id == assetId);
            var result = ValidateAsset(spec, spec.materials.ToDictionary(material => material.sourceName,
                material => AssetDatabase.LoadAssetAtPath<Material>(OutputRoot + "/Materials/" + spec.id + "_" + material.sourceName + ".mat"), StringComparer.Ordinal));
            Require(Fingerprint(before) == Fingerprint(InputSnapshot(descriptorPath, descriptor)), "Golden inputs changed during promotion validation.");
            return result;
        }
    }
}
