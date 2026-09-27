using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Direct references to reviewed Golden prefabs. Never copies, flattens or rewrites their native structure.</summary>
    public sealed class GoldenProductionBindings
    {
        private readonly Dictionary<string, GameObject> prefabs = new Dictionary<string, GameObject>(StringComparer.Ordinal);
        private GoldenProductionGate.Binding[] entries = Array.Empty<GoldenProductionGate.Binding>();
        private GoldenProductionBindings() { }

        public static GoldenProductionBindings Load(string manifestPath = GoldenProductionGate.DefaultManifest)
        {
            var result = new GoldenProductionBindings();
            // Missing optional default keeps existing production content unchanged. An explicitly requested path must exist.
            if (manifestPath == GoldenProductionGate.DefaultManifest && !File.Exists(manifestPath)) return result;
            var gate = NewGate();
            var manifest = gate.Read(manifestPath);
            result.entries = manifest.bindings;
            foreach (var binding in manifest.bindings)
            {
                GoldenSampleBuilder.ValidatePromotionSource(binding.descriptor.path, binding.assetId, binding.nativeImport.path);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(binding.prefab.path);
                if (prefab == null || !PrefabUtility.IsPartOfPrefabAsset(prefab)) throw new InvalidOperationException("Accepted Golden prefab unavailable: " + binding.assetId);
                // Native validation loads prefab contents read-only. Verify that it did not alter any accepted byte.
                gate.ValidateBinding(binding);
                var acceptance = gate.ReadJson<GoldenProductionGate.VisualAcceptance>(binding.acceptance.path);
                foreach (var comparison in acceptance.comparisons)
                    GoldenProductionCapture.ValidateEvidenceImage(gate.ReadJson<GoldenProductionGate.CaptureEvidence>(comparison.capture.path));
                result.prefabs.Add(binding.semanticName, prefab);
            }
            return result;
        }

        public GameObject Resolve(string semanticName, Func<string, GameObject> legacy)
            => prefabs.TryGetValue(semanticName, out var prefab) ? prefab : legacy(semanticName);

        public void ValidateBound(string semanticName, GameObject actual)
        {
            GoldenProductionGate.ValidateResolvedPrefab(semanticName, actual == null ? null : AssetDatabase.GetAssetPath(actual), entries);
        }

        public void ValidateConsumed(IEnumerable<string> supportedNames)
        {
            var supported = new HashSet<string>(supportedNames, StringComparer.Ordinal);
            foreach (string name in prefabs.Keys)
                if (!supported.Contains(name)) throw new InvalidOperationException("Promotion names an unsupported pack slot: " + name);
        }

        public static GoldenProductionGate NewGate() => new GoldenProductionGate(Directory.GetCurrentDirectory(), (json, type) => JsonUtility.FromJson(json, type));
        public static GoldenProductionGate.FileRef ManifestIdentity() => File.Exists(GoldenProductionGate.DefaultManifest) ? NewGate().Bind(GoldenProductionGate.DefaultManifest) : null;
        public static void RequireSameManifest(GoldenProductionGate.FileRef before)
        {
            var after = ManifestIdentity();
            if ((before == null) != (after == null) || before != null && (before.path != after.path || before.sha256 != after.sha256))
                throw new InvalidOperationException("Promotion manifest changed during the content build.");
        }
    }
}
