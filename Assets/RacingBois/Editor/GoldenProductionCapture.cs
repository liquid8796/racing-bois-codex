using System;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Real, hash-bound native camera evidence. It deliberately cannot create an accepted review.</summary>
    public static class GoldenProductionCapture
    {
        public const string CaptureRoot = "docs/p08/promotion/captures/";

        public static string Capture(string descriptorPath, string assetId, string importReceiptPath,
            GameObject subject, Camera camera, string view, string conceptView, string newImagePath, int width = 1920, int height = 1080)
        {
            if (EditorApplication.isCompiling || EditorApplication.isPlayingOrWillChangePlaymode || subject == null || camera == null || !subject.activeInHierarchy || width < 640 || height < 360 || width > 7680 || height > 4320)
                throw new InvalidOperationException("Capture requires a stable native scene, visible subject, camera and bounded dimensions.");
            var native = GoldenSampleBuilder.ValidatePromotionSource(descriptorPath, assetId, importReceiptPath);
            var gate = GoldenProductionBindings.NewGate();
            var spec = gate.ReadJson<GoldenProductionGate.Descriptor>(descriptorPath).assets.Single(x => x.id == assetId);
            var views = spec.kind == "environment" ? GoldenProductionGate.EnvironmentViews : GoldenProductionGate.ActorViews;
            if (!views.Contains(view) || string.IsNullOrWhiteSpace(conceptView) || conceptView.Trim().Length < 8)
                throw new InvalidOperationException("Name the required view and the exact corresponding region/view of the locked concept.");
            string receiptPath = Path.ChangeExtension(newImagePath, ".capture.json");
            NewPath(newImagePath); NewPath(receiptPath);
            if (!newImagePath.EndsWith(".png", StringComparison.Ordinal)) throw new InvalidOperationException("Capture output must be PNG.");
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(native.prefab);
            ValidateCaptureInstance(subject, prefab);
            var visible = subject.GetComponentsInChildren<Renderer>(false).Where(x => x.enabled && !x.forceRenderingOff && (camera.cullingMask & (1 << x.gameObject.layer)) != 0).ToArray();
            var planes = GeometryUtility.CalculateFrustumPlanes(camera);
            if (visible.Length == 0 || !visible.Any(x => GeometryUtility.TestPlanesAABB(planes, x.bounds)))
                throw new InvalidOperationException("Subject has no enabled renderer inside the camera frustum/culling mask.");
            var binding = new GoldenProductionGate.Binding { assetId = assetId, descriptor = gate.Bind(descriptorPath), nativeImport = gate.Bind(importReceiptPath), prefab = gate.Bind(native.prefab) };
            var concept = gate.Bind(spec.concept.path);
            var target = RenderTexture.GetTemporary(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            var previous = RenderTexture.active;
            Texture2D pixels = null;
            GameObject captureSubject = null;
            bool originalActive = subject.activeSelf;
            try
            {
                // ForceLOD has no public getter. A fresh owned instance avoids mutating or guessing
                // the caller's hidden forced-LOD state, and is always discarded after this render.
                captureSubject = (GameObject)PrefabUtility.InstantiatePrefab(prefab, subject.scene);
                captureSubject.transform.SetPositionAndRotation(subject.transform.position, subject.transform.rotation);
                ValidateCaptureInstance(captureSubject, prefab);
                foreach (var group in captureSubject.GetComponentsInChildren<LODGroup>(true))
                {
                    if (!group.enabled || !group.gameObject.activeInHierarchy) throw new InvalidOperationException("Capture LOD group is disabled.");
                    group.ForceLOD(0);
                }
                subject.SetActive(false);
                var request = new UniversalRenderPipeline.SingleCameraRequest { destination = target };
                if (!RenderPipeline.SupportsRenderRequest(camera, request)) throw new InvalidOperationException("URP camera render request unavailable.");
                RenderPipeline.SubmitRenderRequest(camera, request); RenderTexture.active = target;
                pixels = new Texture2D(width, height, TextureFormat.RGBA32, false, false);
                pixels.ReadPixels(new Rect(0, 0, width, height), 0, 0); pixels.Apply(false, false);
                var colors = pixels.GetPixels32(); var first = colors[0];
                if (!Enumerable.Range(1, (colors.Length - 1) / 31).Any(i => Math.Abs(colors[i * 31].r - first.r) + Math.Abs(colors[i * 31].g - first.g) + Math.Abs(colors[i * 31].b - first.b) > 20))
                    throw new InvalidOperationException("Uniform pixels are not usable visual evidence.");
                gate.Verify(binding.descriptor); gate.Verify(binding.nativeImport); gate.Verify(binding.prefab); gate.Verify(concept);
                ValidateCaptureInstance(captureSubject, prefab);
                Directory.CreateDirectory(Path.GetDirectoryName(newImagePath));
                byte[] png = pixels.EncodeToPNG();
                WriteNew(newImagePath, png);
                var evidence = new GoldenProductionGate.CaptureEvidence
                {
                    schema = 1, completed = true, assetId = assetId, view = view, conceptView = conceptView, engine = "UnityEditor", lodPolicy = "fresh-instance-lod0",
                    capturedUtc = DateTimeOffset.UtcNow.ToString("O", CultureInfo.InvariantCulture), width = width, height = height,
                    descriptor = binding.descriptor, nativeImport = binding.nativeImport, prefab = binding.prefab, concept = concept, image = gate.Bind(newImagePath),
                    cameraState = JsonUtility.ToJson(new CameraState { schema = 1, scene = camera.gameObject.scene.path, position = camera.transform.position, rotation = camera.transform.rotation,
                        fieldOfView = camera.fieldOfView, orthographic = camera.orthographic, orthographicSize = camera.orthographicSize, cullingMask = camera.cullingMask,
                        background = camera.backgroundColor, clearFlags = camera.clearFlags.ToString() }),
                    subjectState = JsonUtility.ToJson(new SubjectState { schema = 1, prefab = native.prefab, scene = captureSubject.scene.path, position = captureSubject.transform.position, rotation = captureSubject.transform.rotation,
                        scale = captureSubject.transform.lossyScale, rendererPaths = captureSubject.GetComponentsInChildren<Renderer>(true).Select(x => Relative(captureSubject.transform, x.transform)).ToArray() })
                };
                gate.ValidateCapture(evidence, binding, concept);
                WriteNew(receiptPath, System.Text.Encoding.UTF8.GetBytes(JsonUtility.ToJson(evidence, true)));
                return receiptPath;
            }
            finally
            {
                if (captureSubject != null) UnityEngine.Object.DestroyImmediate(captureSubject);
                if (subject != null) subject.SetActive(originalActive);
                if (pixels != null) UnityEngine.Object.DestroyImmediate(pixels);
                RenderTexture.active = previous; RenderTexture.ReleaseTemporary(target);
            }
        }

        public static void ValidateCaptureInstance(GameObject subject, GameObject prefab)
        {
            if (prefab == null || PrefabUtility.GetCorrespondingObjectFromOriginalSource(subject) != prefab)
                throw new InvalidOperationException("Subject must be an instance of the exact validated Golden prefab.");
            // This first promotion contract captures the unchanged authored rest state. Animated/posed
            // acceptance needs a future explicit clip/time contract; scene overrides cannot impersonate it.
            if (subject.transform.lossyScale != Vector3.one) throw new InvalidOperationException("Capture subject must retain metre scale.");
            var sourceTransforms = prefab.GetComponentsInChildren<Transform>(true);
            var actualTransforms = subject.GetComponentsInChildren<Transform>(true);
            if (sourceTransforms.Length != actualTransforms.Length) throw new InvalidOperationException("Capture instance hierarchy changed.");
            foreach (var source in sourceTransforms)
            {
                string path = Relative(prefab.transform, source);
                var current = path.Length == 0 ? subject.transform : subject.transform.Find(path);
                if (current == null || source.gameObject.activeSelf != current.gameObject.activeSelf || source.gameObject.layer != current.gameObject.layer ||
                    (path.Length != 0 && (source.localPosition != current.localPosition || source.localRotation != current.localRotation || source.localScale != current.localScale)))
                    throw new InvalidOperationException("Capture instance transform, layer or visibility differs from the prefab.");
            }
            foreach (var modification in PrefabUtility.GetPropertyModifications(subject) ?? Array.Empty<PropertyModification>())
            {
                bool rootPose = modification.target == prefab.transform && (modification.propertyPath.StartsWith("m_LocalPosition.", StringComparison.Ordinal) || modification.propertyPath.StartsWith("m_LocalRotation.", StringComparison.Ordinal) || modification.propertyPath.StartsWith("m_LocalEulerAnglesHint.", StringComparison.Ordinal));
                bool rootName = modification.target == prefab && modification.propertyPath == "m_Name";
                if (!rootPose && !rootName) throw new InvalidOperationException("Unapproved prefab property override in capture: " + modification.propertyPath);
            }
            if (PrefabUtility.GetAddedComponents(subject).Count != 0 || PrefabUtility.GetAddedGameObjects(subject).Count != 0 || PrefabUtility.GetRemovedComponents(subject).Count != 0 || PrefabUtility.GetRemovedGameObjects(subject).Count != 0)
                throw new InvalidOperationException("Capture instance added/removed prefab objects.");
            var expected = prefab.GetComponentsInChildren<Renderer>(true);
            var actual = subject.GetComponentsInChildren<Renderer>(true);
            if (expected.Length != actual.Length) throw new InvalidOperationException("Capture instance renderer set changed.");
            foreach (var renderer in expected)
            {
                var instance = actual.Single(x => Relative(subject.transform, x.transform) == Relative(prefab.transform, renderer.transform));
                if (renderer.GetType() != instance.GetType() || renderer.enabled != instance.enabled || instance.forceRenderingOff || instance.HasPropertyBlock() || !renderer.sharedMaterials.SequenceEqual(instance.sharedMaterials) || Mesh(renderer) != Mesh(instance))
                    throw new InvalidOperationException("Capture instance mesh/material bindings changed.");
                if (renderer is SkinnedMeshRenderer skin && instance is SkinnedMeshRenderer posed)
                {
                    if (Relative(prefab.transform, skin.rootBone) != Relative(subject.transform, posed.rootBone) || !skin.bones.Select(x => Relative(prefab.transform, x)).SequenceEqual(posed.bones.Select(x => Relative(subject.transform, x))))
                        throw new InvalidOperationException("Capture instance rig binding changed.");
                    for (int i = 0; i < skin.sharedMesh.blendShapeCount; i++)
                        if (skin.GetBlendShapeWeight(i) != posed.GetBlendShapeWeight(i)) throw new InvalidOperationException("Capture instance expression differs from authored rest state.");
                }
            }
            var groups = prefab.GetComponentsInChildren<LODGroup>(true);
            if (groups.Length != subject.GetComponentsInChildren<LODGroup>(true).Length) throw new InvalidOperationException("Capture instance LOD groups changed.");
            foreach (var group in groups)
            {
                string path = Relative(prefab.transform, group.transform);
                var instance = (path.Length == 0 ? subject.transform : subject.transform.Find(path)).GetComponent<LODGroup>();
                var a = group.GetLODs(); var b = instance.GetLODs();
                if (a.Length != b.Length) throw new InvalidOperationException("Capture instance LOD count changed.");
                for (int i = 0; i < a.Length; i++)
                    if (a[i].screenRelativeTransitionHeight != b[i].screenRelativeTransitionHeight || !a[i].renderers.Select(x => Relative(prefab.transform, x.transform)).SequenceEqual(b[i].renderers.Select(x => Relative(subject.transform, x.transform))))
                        throw new InvalidOperationException("Capture instance LOD membership changed.");
            }
        }
        public static void ValidateEvidenceImage(GoldenProductionGate.CaptureEvidence evidence)
        {
            var camera = JsonUtility.FromJson<CameraState>(evidence.cameraState);
            var subject = JsonUtility.FromJson<SubjectState>(evidence.subjectState);
            if (camera == null || subject == null || camera.schema != 1 || subject.schema != 1 || camera.cullingMask == 0 ||
                !Finite(camera.fieldOfView) || camera.fieldOfView <= 0 || camera.fieldOfView >= 180 || !Finite(camera.orthographicSize) || camera.orthographicSize <= 0 ||
                !Finite(camera.position) || !Finite(camera.rotation) || !Finite(subject.position) || !Finite(subject.rotation) || subject.scale != Vector3.one ||
                subject.prefab != evidence.prefab.path || subject.rendererPaths == null || subject.rendererPaths.Length == 0 || string.IsNullOrWhiteSpace(camera.clearFlags))
                throw new InvalidOperationException("Native capture metadata is invalid.");
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            try
            {
                if (!ImageConversion.LoadImage(texture, File.ReadAllBytes(evidence.image.path), false) || texture.width != evidence.width || texture.height != evidence.height)
                    throw new InvalidOperationException("Capture PNG does not decode to its bound dimensions.");
            }
            finally { UnityEngine.Object.DestroyImmediate(texture); }
        }
        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static bool Finite(Vector3 value) => Finite(value.x) && Finite(value.y) && Finite(value.z);
        private static bool Finite(Quaternion value) => Finite(value.x) && Finite(value.y) && Finite(value.z) && Finite(value.w) && Mathf.Abs(value.x * value.x + value.y * value.y + value.z * value.z + value.w * value.w - 1) < .001f;
        private static Mesh Mesh(Renderer renderer) => renderer is SkinnedMeshRenderer skin ? skin.sharedMesh : renderer.GetComponent<MeshFilter>()?.sharedMesh;
        private static string Relative(Transform root, Transform child) => AnimationUtility.CalculateTransformPath(child, root);
        private static void NewPath(string path)
        {
            if (string.IsNullOrEmpty(path) || !path.StartsWith(CaptureRoot, StringComparison.Ordinal) || path.Contains("\\") || path.Contains(":") || path.Split('/').Any(x => x == "." || x == ".." || x.Length == 0) || File.Exists(path) || Directory.Exists(path))
                throw new InvalidOperationException("Use a fresh canonical file under " + CaptureRoot);
            for (var dir = new DirectoryInfo(Path.GetDirectoryName(Path.GetFullPath(path))); dir != null && dir.FullName.Length >= Path.GetFullPath(".").Length; dir = dir.Parent)
                if (dir.Exists && (dir.Attributes & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException("Linked capture directory rejected.");
        }
        private static void WriteNew(string path, byte[] bytes) { using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write)) stream.Write(bytes, 0, bytes.Length); }
        [Serializable] private sealed class CameraState { public int schema; public string scene, clearFlags; public Vector3 position; public Quaternion rotation; public float fieldOfView, orthographicSize; public bool orthographic; public int cullingMask; public Color background; }
        [Serializable] private sealed class SubjectState { public int schema; public string prefab, scene; public Vector3 position, scale; public Quaternion rotation; public string[] rendererPaths; }
    }
}
