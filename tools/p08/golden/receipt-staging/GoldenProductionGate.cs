using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Evidence integrity only. A reviewer must actually compare the captured pixels with the locked concepts.</summary>
    public sealed class GoldenProductionGate
    {
        public const string DefaultManifest = "docs/p08/promotion/production-bindings.json";
        public const string PrefabRoot = "Assets/RacingBois/Golden/Generated/Prefabs/";
        public static readonly string[] ActorViews = { "quarter", "front", "side", "rear", "gameplay", "detail" };
        public static readonly string[] EnvironmentViews = { "gameplay", "detail" };
        public static readonly string[] VisualCriteria = { "silhouette", "proportions", "geometry", "component-placement", "materials", "color", "details" };
        public static readonly string[] EnvironmentSlots = {
            "RB_P06_RockA", "RB_P06_RockB", "RB_P06_Sage", "RB_P06_DryGrass", "RB_P06_Guardrail", "RB_P06_Chevron", "RB_P06_UtilityPole",
            "RB_P08_CityWarehouse", "RB_P08_CityCornerShop", "RB_P08_CityStreetlamp", "RB_P08_CityBusShelter", "RB_P08_CityLoadingGantry", "RB_P08_CityWaterTank",
            "RB_P08_RidgeFir", "RB_P08_RidgeGranite", "RB_P08_RidgeStoneWall", "RB_P08_RidgeTimberHut", "RB_P08_RidgeSnowPole", "RB_P08_RidgeGalleryArch",
            "RB_P08_CoastPalm", "RB_P08_CoastSurfShack", "RB_P08_CoastBeacon", "RB_P08_CoastBridgePier", "RB_P08_CoastBoulder", "RB_P08_CoastBroadleafShrub",
            "RB_P08_OrchardAppleTree", "RB_P08_OrchardBarn", "RB_P08_OrchardSilo", "RB_P08_OrchardFence", "RB_P08_OrchardHayBale", "RB_P08_OrchardProduceKiosk"
        };

        [Serializable] public sealed class FileRef { public string path, sha256; }
        [Serializable] public sealed class Manifest { public int schema; public Binding[] bindings; }
        [Serializable] public sealed class Binding
        {
            public string semanticName, assetId, kind;
            public FileRef descriptor, nativeImport, prefab, acceptance;
        }
        [Serializable] public sealed class VisualAcceptance
        {
            public int schema;
            public string assetId, semanticName, status, reviewer, reviewedUtc;
            public bool visualAccepted;
            public FileRef descriptor, nativeImport, prefab, concept, review;
            public string[] remainingDifferences;
            public Comparison[] comparisons;
        }
        [Serializable] public sealed class Comparison
        {
            public FileRef capture;
            public string view, conceptView, framingReview, lightingReview;
            public Criterion[] criteria;
        }
        [Serializable] public sealed class Criterion { public string aspect, result, observation; }
        [Serializable] public sealed class CaptureEvidence
        {
            public int schema, width, height;
            public bool completed;
            public string assetId, view, conceptView, engine, capturedUtc, lodPolicy;
            public FileRef descriptor, nativeImport, prefab, concept, image;
            // Concrete capture metadata is produced by the native Editor capture method, not by this gate.
            public string cameraState, subjectState;
        }
        // Read-only projections of the existing Golden descriptor/import schemas. Native validation reuses the full original types.
        [Serializable] public sealed class Descriptor { public int schema; public Asset[] assets; }
        [Serializable] public sealed class Asset
        {
            public string id, kind;
            public FileRef concept, conceptReview, source, fbx, moduleLodMap;
            public Material[] materials;
            public FileRef[] clips, previewClips;
        }
        [Serializable] public sealed class Material { public FileRef baseColor, normal, metallicSmoothness, occlusion, emission; }
        [Serializable] public sealed class NativeReceipt
        {
            public int schema;
            public bool passed, sourceBindingPassed;
            public string descriptor, descriptorSha256, failure;
            public FileRef[] inputs, outputs;
            public NativeAsset[] assets;
        }
        [Serializable] public sealed class NativeAsset
        {
            public string id, kind, prefab;
            public bool passed, rootIdentity, materialSlotsPreserved, missingReferencesAbsent, handednessValid, rigValid;
            public long[] lodTriangles;
        }

        private readonly string root;
        private readonly Func<string, Type, object> parse;
        public GoldenProductionGate(string repositoryRoot, Func<string, Type, object> jsonParser)
        {
            root = Path.GetFullPath(repositoryRoot).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            parse = jsonParser ?? throw new ArgumentNullException(nameof(jsonParser));
        }

        public Manifest Read(string manifestPath)
        {
            var manifest = ReadJson<Manifest>(manifestPath);
            Need(manifest != null && manifest.schema == 1 && manifest.bindings != null, "Promotion manifest schema/bindings missing.");
            var names = new HashSet<string>(StringComparer.Ordinal);
            var assets = new HashSet<string>(StringComparer.Ordinal);
            foreach (var binding in manifest.bindings)
            {
                Need(binding != null && SafeId(binding.semanticName) && names.Add(binding.semanticName), "Missing/duplicate semantic binding.");
                Need(SafeId(binding.assetId) && assets.Add(binding.assetId), "Missing/duplicate asset binding.");
                ValidateBinding(binding);
            }
            return manifest;
        }

        public void ValidateBinding(Binding binding)
        {
            Need(binding != null && SafeId(binding.assetId) && SafeId(binding.semanticName), "Invalid binding identity.");
            Need(binding.kind == "bike" || binding.kind == "rider" || binding.kind == "environment", "Unsupported promotion kind.");
            Need(binding.kind != "bike" || CatalogName(binding.semanticName, "RB_P08_Bike_", 15), "Bike binding must name its catalog slot.");
            Need(binding.kind != "rider" || CatalogName(binding.semanticName, "RB_P08_Rider_", 8), "Rider binding must name its catalog slot.");
            Need(binding.kind != "environment" || EnvironmentSlots.Contains(binding.semanticName), "Environment cannot occupy an actor or unsupported slot.");
            Verify(binding.descriptor); Verify(binding.nativeImport); Verify(binding.prefab); Verify(binding.acceptance);
            Need(binding.prefab.path == PrefabRoot + binding.assetId + ".prefab", "Use the unchanged generated Golden prefab.");
            var descriptor = ReadJson<Descriptor>(binding.descriptor.path);
            Need(descriptor != null && descriptor.schema == 1 && descriptor.assets != null, "Invalid Golden descriptor.");
            var matches = descriptor.assets.Where(x => x != null && x.id == binding.assetId).ToArray();
            Need(matches.Length == 1 && matches[0].kind == binding.kind, "Descriptor does not identify the requested asset/kind.");
            var asset = matches[0];
            var native = ReadJson<NativeReceipt>(binding.nativeImport.path);
            Need(native != null && native.schema == 1 && GoldenReceiptFiles.ImportSucceeded(native.passed, native.sourceBindingPassed, native.failure), "Successful source-bound native import required.");
            Need(native.descriptor == binding.descriptor.path && SameHash(native.descriptorSha256, binding.descriptor.sha256), "Native import belongs to another descriptor.");
            VerifySet(native.inputs); VerifySet(native.outputs);
            Need(Contains(native.inputs, binding.descriptor) && Contains(native.outputs, binding.prefab), "Native receipt does not bind descriptor/prefab bytes.");
            foreach (var input in Inputs(asset)) { Verify(input); Need(Contains(native.inputs, input), "Descriptor input absent from native receipt: " + input.path); }
            var nativeAssets = (native.assets ?? Array.Empty<NativeAsset>()).Where(x => x != null && x.id == binding.assetId).ToArray();
            Need(nativeAssets.Length == 1, "Native asset result missing/duplicated.");
            var result = nativeAssets[0];
            Need(result.prefab == binding.prefab.path && result.kind == binding.kind && result.passed && result.rootIdentity && result.materialSlotsPreserved && result.missingReferencesAbsent,
                "Native prefab/material/reference gates incomplete.");
            Need(result.lodTriangles != null && result.lodTriangles.Length == 3 && result.lodTriangles[0] > result.lodTriangles[1] && result.lodTriangles[1] > result.lodTriangles[2] && result.lodTriangles[2] > 0, "Three decreasing native LODs required.");
            Need(binding.kind == "environment" || result.handednessValid, "Native actor handedness incomplete.");
            Need(binding.kind != "rider" || result.rigValid, "Native rider rig/clip gates incomplete.");

            var acceptance = ReadJson<VisualAcceptance>(binding.acceptance.path);
            Need(acceptance != null && acceptance.schema == 1 && acceptance.visualAccepted && acceptance.status == "accepted", "Explicit accepted visual review required; current candidates are not accepted.");
            Need(acceptance.assetId == binding.assetId && acceptance.semanticName == binding.semanticName && Same(acceptance.descriptor, binding.descriptor) && Same(acceptance.nativeImport, binding.nativeImport) && Same(acceptance.prefab, binding.prefab) && Same(acceptance.concept, asset.concept), "Visual review is for different semantic identity, inputs or reference version.");
            Need(!string.IsNullOrWhiteSpace(acceptance.reviewer) && Utc(acceptance.reviewedUtc), "Named reviewer and UTC review time required.");
            Need(acceptance.remainingDifferences != null && acceptance.remainingDifferences.Length == 0, "Unresolved or omitted difference list cannot be accepted.");
            Verify(acceptance.review);
            Need(Path.GetExtension(acceptance.review.path).Equals(".md", StringComparison.OrdinalIgnoreCase) && File.ReadAllText(FullPath(acceptance.review.path)).Trim().Length >= 80, "A substantive preserved comparison review is required.");
            Need(acceptance.comparisons != null, "Corresponding-view comparisons required.");
            string[] views = binding.kind == "environment" ? EnvironmentViews : ActorViews;
            Need(acceptance.comparisons.Length == views.Length && acceptance.comparisons.Select(x => x?.view).OrderBy(x => x, StringComparer.Ordinal).SequenceEqual(views.OrderBy(x => x, StringComparer.Ordinal)), "Required corresponding views missing/duplicated.");
            var images = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var comparison in acceptance.comparisons)
            {
                Need(Text(comparison.conceptView) && Text(comparison.framingReview) && Text(comparison.lightingReview), "Explicit reference-view, framing and lighting reviews required.");
                Need(comparison.criteria != null && comparison.criteria.Length == VisualCriteria.Length && comparison.criteria.Select(x => x?.aspect).OrderBy(x => x, StringComparer.Ordinal).SequenceEqual(VisualCriteria.OrderBy(x => x, StringComparer.Ordinal)), "Every visual dimension must be reviewed once.");
                Need(comparison.criteria.All(x => x.result == "match" && Text(x.observation)), "Blank or mismatching visual dimensions cannot pass.");
                Verify(comparison.capture);
                var capture = ReadJson<CaptureEvidence>(comparison.capture.path);
                ValidateCapture(capture, binding, asset.concept);
                Need(capture.view == comparison.view && capture.conceptView == comparison.conceptView, "Capture/reference view does not match review.");
                Need(images.Add(capture.image.sha256), "Duplicate pixels cannot stand in for different required views.");
                Need(DateTimeOffset.Parse(capture.capturedUtc, CultureInfo.InvariantCulture) <= DateTimeOffset.Parse(acceptance.reviewedUtc, CultureInfo.InvariantCulture), "Review predates its capture.");
            }
        }

        public void ValidateCapture(CaptureEvidence capture, Binding binding, FileRef concept)
        {
            Need(capture != null && capture.schema == 1 && capture.completed && capture.engine == "UnityEditor", "Source-bound native Unity capture required.");
            Need(capture.lodPolicy == "fresh-instance-lod0", "Capture must declare controlled LOD0 on a fresh prefab instance.");
            Need(capture.assetId == binding.assetId && Same(capture.descriptor, binding.descriptor) && Same(capture.nativeImport, binding.nativeImport) && Same(capture.prefab, binding.prefab) && Same(capture.concept, concept), "Capture is stale or belongs to another actor/reference/import.");
            Need(Utc(capture.capturedUtc) && Text(capture.cameraState) && Text(capture.subjectState) && Text(capture.conceptView), "Capture metadata incomplete.");
            Verify(capture.image);
            Need(!SameHash(capture.image.sha256, concept.sha256), "Concept image is not a runtime capture.");
            Need(Path.GetExtension(capture.image.path).Equals(".png", StringComparison.OrdinalIgnoreCase), "PNG capture required.");
            using (var stream = File.OpenRead(FullPath(capture.image.path)))
            {
                byte[] header = new byte[24];
                Need(stream.Length > 1000 && stream.Read(header, 0, header.Length) == header.Length && header.Take(8).SequenceEqual(new byte[] {137,80,78,71,13,10,26,10}) && System.Text.Encoding.ASCII.GetString(header, 12, 4) == "IHDR", "Invalid or undersized PNG evidence.");
                int width = BigEndian(header, 16), height = BigEndian(header, 20);
                Need(width == capture.width && height == capture.height && width >= 640 && height >= 360 && width <= 7680 && height <= 4320, "Capture dimensions differ from actual PNG or exceed capture bounds.");
            }
        }

        public T ReadJson<T>(string path) where T : class => parse(File.ReadAllText(FullPath(path)), typeof(T)) as T;
        public static void ValidateResolvedPrefab(string semanticName, string actualPath, Binding[] bindings)
        {
            var binding = (bindings ?? Array.Empty<Binding>()).SingleOrDefault(x => x.semanticName == semanticName);
            if (binding != null) Need(actualPath == binding.prefab.path, "Pack does not reference the exact accepted Golden prefab: " + semanticName);
            else Need(actualPath == null || !actualPath.StartsWith("Assets/RacingBois/Golden/", StringComparison.OrdinalIgnoreCase), "Golden prefab has no active accepted binding: " + semanticName);
        }
        public FileRef Bind(string path) => new FileRef { path = path, sha256 = Hash(FullPath(path)) };
        public void Verify(FileRef file)
        {
            Need(file != null && ValidHash(file.sha256), "Explicit path and SHA256 required.");
            Need(SameHash(Hash(FullPath(file.path)), file.sha256), "Bound file changed: " + file.path);
        }
        public string FullPath(string path)
        {
            Need(!string.IsNullOrWhiteSpace(path) && !Path.IsPathRooted(path) && !path.Contains("\\") && !path.Contains(":") && !path.Split('/').Any(x => x == "." || x == ".." || x.Length == 0), "Canonical repository-relative path required.");
            string full = Path.GetFullPath(Path.Combine(root, path));
            Need(full.StartsWith(root, StringComparison.OrdinalIgnoreCase) && File.Exists(full), "File missing/outside repository: " + path);
            Need((File.GetAttributes(full) & FileAttributes.ReparsePoint) == 0, "Linked evidence is not accepted.");
            for (var folder = new DirectoryInfo(Path.GetDirectoryName(full)); folder != null && folder.FullName.Length >= root.Length - 1; folder = folder.Parent)
                Need((folder.Attributes & FileAttributes.ReparsePoint) == 0, "Linked evidence directory is not accepted.");
            return full;
        }
        private void VerifySet(FileRef[] files)
        {
            Need(files != null && files.Length > 0 && files.All(x => x != null) && files.Select(x => x.path).Distinct(StringComparer.OrdinalIgnoreCase).Count() == files.Length, "Native bound file set empty/duplicated.");
            foreach (var file in files) Verify(file);
        }
        private static IEnumerable<FileRef> Inputs(Asset asset)
        {
            yield return asset.concept; yield return asset.conceptReview; yield return asset.source; yield return asset.fbx;
            if (asset.moduleLodMap != null && !string.IsNullOrEmpty(asset.moduleLodMap.path)) yield return asset.moduleLodMap;
            Need(asset.materials != null && asset.materials.Length > 0, "Descriptor materials missing.");
            foreach (var material in asset.materials)
            {
                Need(material != null, "Null descriptor material.");
                yield return material.baseColor; yield return material.normal; yield return material.metallicSmoothness;
                if (material.occlusion != null && !string.IsNullOrEmpty(material.occlusion.path)) yield return material.occlusion;
                if (material.emission != null && !string.IsNullOrEmpty(material.emission.path)) yield return material.emission;
            }
            foreach (var file in (asset.clips ?? Array.Empty<FileRef>()).Concat(asset.previewClips ?? Array.Empty<FileRef>())) yield return file;
        }
        private static bool CatalogName(string value, string prefix, int count) => Enumerable.Range(0, count).Any(i => value == prefix + i.ToString("D2", CultureInfo.InvariantCulture));
        private static bool SafeId(string value) => !string.IsNullOrEmpty(value) && value.All(c => c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || c == '_' || c == '-' || c == '.');
        private static bool Text(string value) => !string.IsNullOrWhiteSpace(value) && value.Trim().Length >= 8;
        private static bool Utc(string value) => DateTimeOffset.TryParseExact(value, "O", CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var time) && time.Offset == TimeSpan.Zero;
        private static bool ValidHash(string value) => value != null && value.Length == 64 && value.All(Uri.IsHexDigit);
        private static bool SameHash(string a, string b) => ValidHash(a) && ValidHash(b) && string.Equals(a, b, StringComparison.OrdinalIgnoreCase);
        private static bool Same(FileRef a, FileRef b) => a != null && b != null && a.path == b.path && SameHash(a.sha256, b.sha256);
        private static bool Contains(FileRef[] files, FileRef expected) => files.Any(x => Same(x, expected));
        private static int BigEndian(byte[] bytes, int offset) => (bytes[offset] << 24) | (bytes[offset + 1] << 16) | (bytes[offset + 2] << 8) | bytes[offset + 3];
        private static string Hash(string path) { using (var stream = File.OpenRead(path)) using (var hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
        private static void Need(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
    }
}
