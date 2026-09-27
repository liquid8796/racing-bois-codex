using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        public const string OutputRoot = "Assets/RacingBois/Golden/Generated";
        public const string ScenePath = OutputRoot + "/GoldenReview.unity";
        public const string ReceiptRoot = "docs/p08/golden/unity";

        [Serializable] public sealed class Descriptor { public int schema; public AssetSpec[] assets; }
        [Serializable] public sealed class InputFile { public string path, sha256; }
        [Serializable] public sealed class AssetSpec
        {
            public string id, kind;
            public string restPose = "file";
            public string lightmapUv = "generated";
            public InputFile moduleLodMap;
            public InputFile concept, conceptReview, source, fbx;
            public Vector3 modelRotationEuler, minimumSize, maximumSize;
            public float maximumBelowGround = .04f;
            public MaterialSpec[] materials;
            public LodSpec[] lods;
            public string[] wheelPivots, groundMarkers, requiredBones;
            public string forwardMarker, leftMarker, rightMarker, rigRoot;
            public ClipSpec[] clips;
            public ClipSpec[] previewClips;
            public string[] loopClips;
            public ColliderSpec[] colliders;
            public bool isStatic;
        }
        [Serializable] public sealed class MaterialSpec
        {
            public string sourceName;
            public InputFile baseColor, normal, metallicSmoothness, occlusion, emission;
            public int maxSize = 2048;
            public bool transparent, doubleSided;
            public float opacity = 1f, normalScale = 1f, emissionIntensity = 1f;
        }
        [Serializable] public sealed class LodSpec { public float height; public string[] rendererPaths; }
        [Serializable] public sealed class ClipSpec { public string path, sha256, name; }
        [Serializable] public sealed class ColliderSpec
        {
            public string type;
            public Vector3 center, size;
            public float radius, height;
            public int direction = 1;
        }
        [Serializable] public sealed class FileReceipt { public string path, sha256; public long bytes; }
        [Serializable] public sealed class AssetReceipt
        {
            public string id, prefab, kind;
            public bool passed, rootIdentity, materialSlotsPreserved, missingReferencesAbsent, rigValid, handednessValid;
            public int materialCount, colliderCount, rendererCount, clipsSampled;
            public long sampledVertices;
            public Vector3 bounds;
            public long[] lodTriangles;
        }
        [Serializable] public sealed class ImportReceipt
        {
            public int schema = 1;
            public string attemptId, utc, unityVersion, descriptor, descriptorSha256, sourceFingerprint, failure;
            public bool passed, sourceBindingPassed;
            public FileReceipt[] inputs, outputs;
            public AssetReceipt[] assets;
            public string scope = "Exact-input Unity import, materials, prefab, LOD and rig structure only. Visual quality, concept fidelity, deformation appearance, contacts and performance require separate approval.";
        }

        public static Descriptor ReadDescriptor(string descriptorPath)
        {
            VerifyCompiledSources();
            ProjectPath(descriptorPath, false);
            var descriptor = JsonUtility.FromJson<Descriptor>(File.ReadAllText(descriptorPath));
            Require(descriptor != null && descriptor.schema == 1 && descriptor.assets != null && descriptor.assets.Length > 0,
                "Golden descriptor schema 1 and at least one actual asset are required.");
            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var asset in descriptor.assets)
            {
                Require(asset != null && SafeId(asset.id) && ids.Add(asset.id), "Missing/duplicate/unsafe asset ID.");
                Require(asset.kind == "bike" || asset.kind == "rider" || asset.kind == "environment", "Unsupported golden asset kind: " + asset.id);
                VerifyInput(asset.concept); VerifyInput(asset.conceptReview); VerifyInput(asset.source); VerifyInput(asset.fbx);
                Require(string.IsNullOrEmpty(asset.restPose) || asset.restPose == "file" || (asset.kind == "rider" && asset.restPose == "bind"), "Invalid rest-pose policy.");
                Require(asset.lightmapUv == "generated" || (asset.isStatic && asset.lightmapUv == "authored") ||
                    (asset.isStatic && asset.kind == "environment" && asset.lightmapUv == "none"), "Invalid lightmap UV policy.");
                Require(asset.fbx.path.StartsWith("Assets/", StringComparison.Ordinal) && asset.fbx.path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase), "FBX must be a project asset.");
                Require(asset.minimumSize.x > 0 && asset.minimumSize.y > 0 && asset.minimumSize.z > 0 &&
                    asset.maximumSize.x >= asset.minimumSize.x && asset.maximumSize.y >= asset.minimumSize.y && asset.maximumSize.z >= asset.minimumSize.z,
                    "Physical size envelope is missing: " + asset.id);
                Require(asset.materials != null && asset.materials.Length > 0, "Explicit material bindings are required: " + asset.id);
                var names = new HashSet<string>(StringComparer.Ordinal);
                foreach (var material in asset.materials)
                {
                    Require(material != null && SafeId(material.sourceName) && names.Add(material.sourceName), "Invalid/duplicate source material name: " + asset.id);
                    Require(material.maxSize >= 512 && material.maxSize <= 4096 && (material.maxSize & (material.maxSize - 1)) == 0,
                        "Texture limit must be a power of two between 512 and 4096.");
                    Require(material.opacity > 0 && material.opacity <= 1 && material.normalScale >= 0 && material.normalScale <= 2,
                        "Invalid material parameters: " + material.sourceName);
                    VerifyInput(material.baseColor); VerifyInput(material.normal); VerifyInput(material.metallicSmoothness);
                    if (HasInput(material.occlusion)) VerifyInput(material.occlusion);
                    if (HasInput(material.emission)) VerifyInput(material.emission);
                }
                Require(asset.lods != null && asset.lods.Length == 3, "Exactly three LODs are required: " + asset.id);
                float previous = 1.01f;
                var rendererPaths = new HashSet<string>(StringComparer.Ordinal);
                foreach (var lod in asset.lods)
                {
                    Require(lod != null && lod.height > 0 && lod.height < previous && lod.rendererPaths != null && lod.rendererPaths.Length > 0,
                        "LOD heights must decrease and renderer lists must be populated: " + asset.id);
                    previous = lod.height;
                    foreach (var path in lod.rendererPaths)
                        Require(!string.IsNullOrWhiteSpace(path) && rendererPaths.Add(path), "Renderer occurs in more than one LOD: " + asset.id);
                }
                if (HasInput(asset.moduleLodMap)) ReadModuleLodMap(asset.moduleLodMap, asset);
                Require(!string.IsNullOrWhiteSpace(asset.forwardMarker) && asset.groundMarkers != null && asset.groundMarkers.Length > 0,
                    "Explicit forward and ground markers are required: " + asset.id);
                Require(!float.IsNaN(asset.maximumBelowGround) && !float.IsInfinity(asset.maximumBelowGround) && asset.maximumBelowGround >= 0
                    && asset.maximumBelowGround <= (asset.kind == "environment" ? 1000f : .04f), "Invalid below-anchor depth allowance: " + asset.id);
                if (asset.kind == "bike" || asset.kind == "rider")
                    Require(!string.IsNullOrWhiteSpace(asset.leftMarker) && !string.IsNullOrWhiteSpace(asset.rightMarker) && asset.leftMarker != asset.rightMarker,
                        "Actor requires explicit semantic left/right markers: " + asset.id);
                if (asset.kind == "bike") Require(asset.wheelPivots != null && asset.wheelPivots.Length == 2, "Bike requires two axle pivots.");
                if (asset.kind == "rider")
                {
                    Require(!string.IsNullOrWhiteSpace(asset.rigRoot) && asset.requiredBones != null && asset.requiredBones.Length >= 15,
                        "Rider requires a declared rig and deform bone paths.");
                    Require(asset.clips != null && asset.clips.Length > 0, "Rider requires actual animation clips to sample.");
                    var identities = new HashSet<string>(StringComparer.Ordinal);
                    foreach (var clip in AllClips(asset))
                    {
                        Require(clip != null && !string.IsNullOrWhiteSpace(clip.name) && identities.Add(clip.path + "|" + clip.name), "Unique clip identity required.");
                        VerifyInput(new InputFile { path = clip.path, sha256 = clip.sha256 });
                    }
                    if (asset.loopClips != null)
                    {
                        Require(asset.loopClips.Distinct(StringComparer.Ordinal).Count() == asset.loopClips.Length, "Duplicate loop clip declaration.");
                        Require(AllClips(asset).All(clip => clip.path == asset.fbx.path), "Explicit loop policy requires clips in the declared FBX.");
                        Require(asset.loopClips.All(name => AllClips(asset).Any(clip => clip.name == name)), "Loop policy refers to an undeclared clip.");
                    }
                }
                foreach (var collider in asset.colliders ?? Array.Empty<ColliderSpec>())
                    Require(collider.type == "box" && collider.size.x > 0 && collider.size.y > 0 && collider.size.z > 0 ||
                        collider.type == "capsule" && collider.radius > 0 && collider.height >= collider.radius * 2 && collider.direction >= 0 && collider.direction <= 2,
                        "Only valid, explicitly sized box/capsule colliders are accepted.");
            }
            return descriptor;
        }

        private static bool SafeId(string value) => !string.IsNullOrWhiteSpace(value) && value.All(c => char.IsLetterOrDigit(c) || c == '_' || c == '-' || c == '.');
        private static bool HasInput(InputFile input) => input != null && !string.IsNullOrWhiteSpace(input.path);
        private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
        private static void VerifyInput(InputFile input)
        {
            Require(HasInput(input) && input.sha256 != null && input.sha256.Length == 64 && input.sha256.All(Uri.IsHexDigit), "Input path and SHA-256 are required.");
            string fullPath = ProjectPath(input.path, false);
            Require(File.Exists(fullPath), "Required golden input missing: " + input.path);
            Require(Digest(fullPath).Equals(input.sha256, StringComparison.OrdinalIgnoreCase), "Golden source hash changed: " + input.path);
        }
        private static string ProjectPath(string path, bool allowMissing)
        {
            Require(!string.IsNullOrWhiteSpace(path) && !Path.IsPathRooted(path), "Use repository-relative paths.");
            string root = Path.GetFullPath(".").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(path);
            Require(full.StartsWith(root, StringComparison.OrdinalIgnoreCase), "Path escaped the project: " + path);
            var cursor = new FileInfo(full);
            if (cursor.Exists) Require((cursor.Attributes & FileAttributes.ReparsePoint) == 0, "Linked inputs are not accepted.");
            for (var directory = cursor.Directory; directory != null && directory.FullName.Length >= root.Length; directory = directory.Parent)
                if (directory.Exists) Require((directory.Attributes & FileAttributes.ReparsePoint) == 0, "Linked project paths are not accepted.");
            Require(allowMissing || File.Exists(full), "File missing: " + path);
            return full;
        }
        private static string Digest(string path)
        {
            using (var stream = File.OpenRead(path)) using (var hash = SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        private static IEnumerable<string> AssetInputs(AssetSpec asset)
        {
            yield return asset.concept.path; yield return asset.conceptReview.path; yield return asset.source.path; yield return asset.fbx.path;
            if (HasInput(asset.moduleLodMap)) yield return asset.moduleLodMap.path;
            foreach (var material in asset.materials)
                foreach (var input in new[] { material.baseColor, material.normal, material.metallicSmoothness, material.occlusion, material.emission })
                    if (HasInput(input)) yield return input.path;
            foreach (var clip in AllClips(asset)) yield return clip.path;
        }
        private static FileReceipt[] InputSnapshot(string descriptorPath, Descriptor descriptor) => descriptor.assets.SelectMany(AssetInputs)
            .Concat(new[] { descriptorPath, "Assets/RacingBois/Editor/RacingBois.Authoring.Editor.asmdef" })
            .Concat(Directory.GetFiles("Assets/RacingBois/Editor", "GoldenSampleBuilder*.cs", SearchOption.TopDirectoryOnly))
            .Concat(Directory.GetFiles("Assets/RacingBois/Golden/Runtime", "*", SearchOption.AllDirectories).Where(path => !path.EndsWith(".meta", StringComparison.Ordinal)))
            .Concat(new[] { "Assets/RacingBois/Client/Presentation/RiderAnimationSet.cs", "Assets/RacingBois/Editor/UrpProfileAuthoring.cs" })
            .Concat(new[] { "RacingBois.Authoring.Editor", "RacingBois.Client.Presentation", "RacingBois.Golden" }
                .SelectMany(name => new[] { "Library/ScriptAssemblies/" + name + ".dll", "Library/ScriptAssemblies/" + name + ".pdb" }))
            .Select(path => path.Replace('\\', '/')).Distinct(StringComparer.Ordinal).OrderBy(p => p, StringComparer.Ordinal).Select(FileRow).ToArray();
        private static FileReceipt FileRow(string path) => new FileReceipt { path = path.Replace('\\', '/'), sha256 = Digest(path), bytes = new FileInfo(path).Length };
        private static string Fingerprint(FileReceipt[] files)
        {
            string value = string.Join("\n", files.Select(file => file.path + "\t" + file.sha256 + "\t" + file.bytes));
            using (var hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-", "").ToLowerInvariant();
        }
    }
}
