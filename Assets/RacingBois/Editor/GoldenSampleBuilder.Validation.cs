using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        public static string Validate(string descriptorPath)
        {
            var descriptor = ReadDescriptor(descriptorPath);
            var receipt = new ImportReceipt
            {
                attemptId = Guid.NewGuid().ToString("N"), unityVersion = Application.unityVersion,
                descriptor = descriptorPath, descriptorSha256 = Digest(descriptorPath), inputs = InputSnapshot(descriptorPath, descriptor)
            };
            receipt.sourceFingerprint = Fingerprint(receipt.inputs);
            try
            {
                var imported = JsonUtility.FromJson<ImportReceipt>(File.ReadAllText(ReceiptRoot + "/import-latest.json"));
                Require(imported != null && imported.passed && imported.sourceBindingPassed && imported.sourceFingerprint == receipt.sourceFingerprint,
                    "Current inputs do not have a matching successful golden import receipt.");
                foreach (var output in imported.outputs) VerifyInput(new InputFile { path = output.path, sha256 = output.sha256 });
                receipt.assets = descriptor.assets.Select(spec => ValidateAsset(spec, spec.materials.ToDictionary(material => material.sourceName,
                    material => AssetDatabase.LoadAssetAtPath<Material>(OutputRoot + "/Materials/" + spec.id + "_" + material.sourceName + ".mat"), StringComparer.Ordinal))).ToArray();
                receipt.sourceBindingPassed = receipt.sourceFingerprint == Fingerprint(InputSnapshot(descriptorPath, descriptor));
                Require(receipt.sourceBindingPassed, "Golden inputs changed during validation.");
                receipt.outputs = imported.outputs;
                receipt.passed = true; WriteReceipt("validation", receipt); return JsonUtility.ToJson(receipt, true);
            }
            catch (Exception error) { receipt.failure = error.GetType().Name + ": " + error.Message; WriteReceipt("validation", receipt); throw; }
        }

        private static AssetReceipt ValidateAsset(AssetSpec spec, Dictionary<string, Material> materials)
        {
            string prefabPath = PrefabPath(spec);
            var root = PrefabUtility.LoadPrefabContents(prefabPath);
            try
            {
                var result = new AssetReceipt { id = spec.id, prefab = prefabPath, kind = spec.kind };
                result.rootIdentity = root.transform.localPosition == Vector3.zero && root.transform.localRotation == Quaternion.identity && root.transform.localScale == Vector3.one;
                Require(result.rootIdentity, "Golden prefab root must be identity: " + spec.id);
                foreach (var transform in root.GetComponentsInChildren<Transform>(true))
                {
                    Require(Finite(transform.localPosition) && Finite(transform.localScale), "Nonfinite prefab transform: " + spec.id);
                    Require(transform.localScale.x > 0 && transform.localScale.y > 0 && transform.localScale.z > 0, "Negative or zero model scale: " + transform.name);
                    foreach (var component in transform.GetComponents<Component>())
                    {
                        Require(component != null, "Missing script: " + transform.name);
                        using (var serialized = new SerializedObject(component))
                        {
                            var property = serialized.GetIterator();
                            while (property.Next(true))
                                if (property.propertyType == SerializedPropertyType.ObjectReference)
                                    Require(property.objectReferenceValue != null || property.objectReferenceEntityIdValue == EntityId.None,
                                        "Missing reference: " + transform.name + "." + property.propertyPath);
                        }
                    }
                }
                result.missingReferencesAbsent = true;
                var model = root.transform.Find("Model"); Require(model != null, "Prefab Model child missing.");
                LOD[] lods;
                if (HasInput(spec.moduleLodMap))
                {
                    var map = ReadModuleLodMap(spec.moduleLodMap, spec);
                    ValidateModuleLodGroups(root, model, spec, map, spec.moduleLodMap);
                    lods = ModuleInspectionLods(root, spec, map);
                }
                else
                {
                    var group = root.GetComponent<LODGroup>();
                    Require(group != null && group.GetLODs().Length == 3, "LODGroup missing.");
                    lods = group.GetLODs();
                }
                var allRenderers = root.GetComponentsInChildren<Renderer>(true);
                Require(lods.SelectMany(lod => lod.renderers).Distinct().Count() == allRenderers.Length, "An exported renderer is outside the declared LOD set.");
                result.rendererCount = allRenderers.Length; result.materialCount = materials.Count;
                result.lodTriangles = new long[3];
                Bounds bounds = default; bool hasBounds = false;
                for (int level = 0; level < 3; level++)
                {
                    Require(Mathf.Abs(lods[level].screenRelativeTransitionHeight - spec.lods[level].height) < .0001f, "LOD threshold changed.");
                    foreach (var renderer in lods[level].renderers)
                    {
                        Require(renderer != null && renderer.sharedMaterials.All(material => material != null && materials.ContainsValue(material)), "Missing/unmapped material.");
                        bool contributesGi = (GameObjectUtility.GetStaticEditorFlags(renderer.gameObject) & StaticEditorFlags.ContributeGI) != 0;
                        Require(contributesGi == (spec.isStatic && spec.lightmapUv != "none"), "Static GI flag differs from explicit lightmap policy.");
                        var mesh = MeshOf(renderer); ValidateMesh(mesh, renderer.sharedMaterials.Length, spec.id,
                            root.transform.worldToLocalMatrix * renderer.transform.localToWorldMatrix);
                        result.lodTriangles[level] += mesh.triangles.LongLength / 3;
                        if (level == 0)
                        {
                            if (spec.lightmapUv == "authored") ValidateSecondaryUv(mesh, renderer.name);
                            var restBounds = CurrentGeometryBounds(renderer);
                            if (hasBounds) bounds.Encapsulate(restBounds);
                            else { bounds = restBounds; hasBounds = true; }
                        }
                        if (renderer is SkinnedMeshRenderer skin) ValidateSkin(skin, model, spec);
                    }
                    if (level > 0) Require(result.lodTriangles[level] < result.lodTriangles[level - 1], "LOD triangle counts must decrease: " + spec.id);
                }
                result.bounds = bounds.size;
                Require(InEnvelope(bounds.size, spec.minimumSize, spec.maximumSize), "Physical model dimensions outside declared envelope: " + spec.id + " " + bounds.size);
                Require(bounds.min.y >= -spec.maximumBelowGround, "Mesh extends below its declared ground-anchor allowance: " + spec.id);
                Vector3 forward = root.transform.InverseTransformPoint(Find(model, spec.forwardMarker).position);
                Require(forward.z > .1f && Mathf.Abs(forward.x) < .02f, "Forward marker must prove Unity +Z: " + spec.id);
                if (!string.IsNullOrWhiteSpace(spec.leftMarker) || !string.IsNullOrWhiteSpace(spec.rightMarker))
                {
                    Require(!string.IsNullOrWhiteSpace(spec.leftMarker) && !string.IsNullOrWhiteSpace(spec.rightMarker), "Left/right marker pair is incomplete.");
                    Vector3 left = root.transform.InverseTransformPoint(Find(model, spec.leftMarker).position);
                    Vector3 right = root.transform.InverseTransformPoint(Find(model, spec.rightMarker).position);
                    Require(left.x < -.01f && right.x > .01f,
                        "Semantic left/right markers must prove Unity -X/+X: " + spec.id + " left=" + left + " right=" + right);
                    result.handednessValid = true;
                }
                foreach (var path in spec.groundMarkers)
                {
                    Vector3 contact = root.transform.InverseTransformPoint(Find(model, path).position);
                    Require(Mathf.Abs(contact.y) < .025f, "Ground contact marker is not on y=0: " + path);
                }
                if (spec.kind == "bike")
                {
                    var front = Find(model, spec.wheelPivots[0]); var rear = Find(model, spec.wheelPivots[1]);
                    Vector3 frontPosition = root.transform.InverseTransformPoint(front.position), rearPosition = root.transform.InverseTransformPoint(rear.position);
                    Require(frontPosition.z > rearPosition.z && Vector3.Distance(frontPosition, rearPosition) > .8f && Vector3.Distance(frontPosition, rearPosition) < 2f,
                        "Bike axle positions do not match positive-forward motorcycle layout.");
                    foreach (var pivot in new[] { front, rear })
                    {
                        Require(pivot.GetComponentsInChildren<Renderer>(true).Length >= 3, "Wheel pivot does not own all three wheel LOD renderers.");
                        foreach (var renderer in pivot.GetComponentsInChildren<Renderer>(true))
                            Require(Vector3.Distance(pivot.position, renderer.bounds.center) < .06f, "Wheel mesh is not axle centered: " + renderer.name);
                    }
                }
                var colliders = root.GetComponentsInChildren<Collider>(true);
                Require(colliders.All(collider => collider is BoxCollider || collider is CapsuleCollider), "Unexpected collider or MeshCollider in golden prefab.");
                Require(colliders.Length == (spec.colliders?.Length ?? 0), "Unexpected extra colliders.");
                result.colliderCount = colliders.Length;
                result.materialSlotsPreserved = true;
                foreach (var binding in spec.materials) ValidateMaterial(spec.id, binding, materials[binding.sourceName]);
                if (spec.kind == "rider")
                {
                    var boundBones = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).SelectMany(skin => skin.bones).Distinct().ToArray();
                    foreach (var path in spec.requiredBones) Require(boundBones.Contains(Find(model, path)), "Required deform bone not bound by any mesh: " + path);
                    result.sampledVertices = SampleAnimations(model.gameObject, spec, false);
                    result.clipsSampled = AllClips(spec).Count(); result.rigValid = true;
                }
                result.passed = true; return result;
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        private static Mesh MeshOf(Renderer renderer)
        {
            if (renderer is SkinnedMeshRenderer skin) return skin.sharedMesh;
            var filter = renderer.GetComponent<MeshFilter>(); Require(filter != null, "MeshFilter missing: " + renderer.name); return filter.sharedMesh;
        }
        private static Bounds CurrentGeometryBounds(Renderer renderer)
        {
            Mesh temporary = null;
            try
            {
                Mesh mesh;
                if (renderer is SkinnedMeshRenderer skin) { temporary = new Mesh(); skin.BakeMesh(temporary, false); mesh = temporary; }
                else mesh = MeshOf(renderer);
                var vertices = mesh.vertices; Require(vertices.Length > 0, "Cannot measure an empty mesh.");
                var bounds = new Bounds(renderer.transform.TransformPoint(vertices[0]), Vector3.zero);
                foreach (var vertex in vertices) bounds.Encapsulate(renderer.transform.TransformPoint(vertex));
                return bounds;
            }
            finally { if (temporary != null) UnityEngine.Object.DestroyImmediate(temporary); }
        }
        private static bool Finite(Vector3 value) => !float.IsNaN(value.x) && !float.IsNaN(value.y) && !float.IsNaN(value.z) && !float.IsInfinity(value.x) && !float.IsInfinity(value.y) && !float.IsInfinity(value.z);
        private static bool InEnvelope(Vector3 value, Vector3 minimum, Vector3 maximum) =>
            value.x >= minimum.x && value.y >= minimum.y && value.z >= minimum.z && value.x <= maximum.x && value.y <= maximum.y && value.z <= maximum.z;

        private static void ValidateMesh(Mesh mesh, int slots, string id, Matrix4x4 localToMetres)
        {
            Require(mesh != null && mesh.vertexCount > 0 && mesh.subMeshCount == slots, "Mesh/submesh/material slot mismatch: " + id);
            Require(mesh.normals.Length == mesh.vertexCount && mesh.tangents.Length == mesh.vertexCount && mesh.uv.Length == mesh.vertexCount,
                "Incomplete vertex channels: " + id);
            var vertices = mesh.vertices;
            Require(vertices.All(Finite) && mesh.normals.All(v => Finite(v) && v.sqrMagnitude > .5f), "Invalid position/normal: " + id);
            Require(mesh.tangents.All(v => Finite(new Vector3(v.x, v.y, v.z)) && Mathf.Abs(Mathf.Abs(v.w) - 1) < .01f), "Invalid tangent basis: " + id);
            var uv = mesh.uv;
            Require(uv.All(v => !float.IsNaN(v.x) && !float.IsNaN(v.y) && !float.IsInfinity(v.x) && !float.IsInfinity(v.y)), "Invalid UV coordinates: " + id);
            var triangles = mesh.triangles;
            Require(triangles.Length > 0 && triangles.Length % 3 == 0 && triangles.All(i => i >= 0 && i < vertices.Length), "Invalid triangle indices.");
            for (int i = 0; i < triangles.Length; i += 3)
            {
                // FBX can store centimetre-sized vertices beneath a compensating transform.
                // Measure edges in the identity prefab's metre space, without adding large terrain translations.
                Vector3 first = localToMetres.MultiplyVector(vertices[triangles[i + 1]] - vertices[triangles[i]]);
                Vector3 second = localToMetres.MultiplyVector(vertices[triangles[i + 2]] - vertices[triangles[i]]);
                Require(Finite(first) && Finite(second) && Vector3.Cross(first, second).sqrMagnitude > 1e-16f,
                    "Degenerate triangle in physical metres: " + id);
                Vector2 a = uv[triangles[i]], b = uv[triangles[i + 1]], c = uv[triangles[i + 2]];
                double uvCross = ((double)b.x - a.x) * ((double)c.y - a.y) - ((double)b.y - a.y) * ((double)c.x - a.x);
                Require(Math.Abs(uvCross) > 1e-14, "Collapsed primary UV triangle: " + id + "/" + mesh.name + " at " + i / 3);
            }
        }

        private static void ValidateSkin(SkinnedMeshRenderer skin, Transform model, AssetSpec spec)
        {
            Require(spec.kind == "rider" && skin.rootBone == Find(model, spec.rigRoot), "Unexpected or incorrect skin root.");
            Require(skin.quality == SkinQuality.Bone4 && skin.bones.Length > 0 && skin.bones.All(bone => bone != null), "Skin bone references/quality invalid.");
            Require(skin.sharedMesh.bindposes.Length == skin.bones.Length, "Bind pose count differs from bone list.");
            var weights = skin.sharedMesh.boneWeights;
            Require(weights.Length == skin.sharedMesh.vertexCount, "Every skinned vertex requires weights.");
            foreach (var weight in weights)
            {
                float total = weight.weight0 + weight.weight1 + weight.weight2 + weight.weight3;
                Require(!float.IsNaN(total) && Mathf.Abs(total - 1) < .002f, "Skin weights are not normalized.");
                foreach (var pair in new[] { Tuple.Create(weight.boneIndex0, weight.weight0), Tuple.Create(weight.boneIndex1, weight.weight1), Tuple.Create(weight.boneIndex2, weight.weight2), Tuple.Create(weight.boneIndex3, weight.weight3) })
                    Require(pair.Item2 >= 0 && (pair.Item2 == 0 || pair.Item1 >= 0 && pair.Item1 < skin.bones.Length), "Invalid skin bone weight/index.");
            }
        }

        private static long SampleAnimations(GameObject model, AssetSpec spec, bool fitBounds)
        {
            var skins = model.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            Require(skins.Length > 0, "Rider has no skinned mesh renderers.");
            var transforms = model.GetComponentsInChildren<Transform>(true);
            var positions = transforms.Select(t => t.localPosition).ToArray(); var rotations = transforms.Select(t => t.localRotation).ToArray(); var scales = transforms.Select(t => t.localScale).ToArray();
            var bounds = new Bounds[skins.Length]; var initialized = new bool[skins.Length];
            var baked = new Mesh(); long count = 0;
            try
            {
                foreach (var clipSpec in AllClips(spec))
                {
                    var clips = AssetDatabase.LoadAllAssetsAtPath(clipSpec.path).OfType<AnimationClip>().Where(clip => clip.name == clipSpec.name).ToArray();
                    Require(clips.Length == 1 && clips[0].length > 0, "Animation clip is missing/ambiguous/empty: " + clipSpec.name);
                    var clip = clips[0]; float moved = 0;
                    if (spec.loopClips != null)
                        Require(clip.isLooping == spec.loopClips.Contains(clipSpec.name), "Imported loop flag differs: " + clipSpec.name);
                    for (int frame = 0; frame <= 16; frame++)
                    {
                        for (int i = 0; i < transforms.Length; i++) { transforms[i].localPosition = positions[i]; transforms[i].localRotation = rotations[i]; transforms[i].localScale = scales[i]; }
                        clip.SampleAnimation(model, clip.length * frame / 16f);
                        for (int i = 0; i < transforms.Length; i++) moved = Mathf.Max(moved, Quaternion.Angle(rotations[i], transforms[i].localRotation));
                        for (int index = 0; index < skins.Length; index++)
                        {
                            skins[index].BakeMesh(baked, false);
                            foreach (var vertex in baked.vertices)
                            {
                                Require(Finite(vertex) && vertex.magnitude < 8f, "Nonfinite/exploding skinned vertex: " + clipSpec.name);
                                if (initialized[index]) bounds[index].Encapsulate(vertex); else { bounds[index] = new Bounds(vertex, Vector3.zero); initialized[index] = true; }
                                if (!fitBounds)
                                {
                                    Bounds tolerated = skins[index].localBounds; tolerated.Expand(.01f);
                                    Require(tolerated.Contains(vertex), "Animation exceeds imported skin bounds: " + clipSpec.name);
                                }
                                count++;
                            }
                        }
                    }
                    Require(moved > .05f, "Clip does not animate the declared hierarchy: " + clipSpec.name);
                }
                if (fitBounds)
                {
                    var envelope = model.GetComponent<RacingBois.Golden.GoldenSkinBounds>();
                    if (envelope == null) envelope = model.AddComponent<RacingBois.Golden.GoldenSkinBounds>();
                    envelope.Entries = new RacingBois.Golden.GoldenSkinBounds.Entry[skins.Length];
                    for (int i = 0; i < skins.Length; i++)
                    {
                        bounds[i].Expand(.06f); skins[i].localBounds = bounds[i];
                        envelope.Entries[i] = new RacingBois.Golden.GoldenSkinBounds.Entry { Renderer = skins[i], Bounds = bounds[i] };
                    }
                }
                return count;
            }
            finally
            {
                for (int i = 0; i < transforms.Length; i++) { transforms[i].localPosition = positions[i]; transforms[i].localRotation = rotations[i]; transforms[i].localScale = scales[i]; }
                UnityEngine.Object.DestroyImmediate(baked);
            }
        }

        private static void ValidateMaterial(string id, MaterialSpec spec, Material material)
        {
            Require(material != null && material.shader != null && material.shader.name == "Universal Render Pipeline/Lit", "Missing or incorrect URP material: " + id);
            Require(material.IsKeywordEnabled("_SURFACE_TYPE_TRANSPARENT") == spec.transparent
                && material.IsKeywordEnabled("_NORMALMAP") && !material.IsKeywordEnabled("_ALPHATEST_ON"),
                "Material surface keywords differ from the declared policy: " + spec.sourceName);
            Require(material.GetFloat("_Cull") == (float)(spec.doubleSided ? UnityEngine.Rendering.CullMode.Off : UnityEngine.Rendering.CullMode.Back)
                && material.doubleSidedGI == spec.doubleSided, "Material sidedness differs from descriptor: " + spec.sourceName);
            foreach (var entry in new[] { Tuple.Create(spec.baseColor, "_BaseMap", false, true), Tuple.Create(spec.normal, "_BumpMap", true, false), Tuple.Create(spec.metallicSmoothness, "_MetallicGlossMap", false, false) })
            {
                Require(AssetDatabase.GetAssetPath(material.GetTexture(entry.Item2)) == entry.Item1.path, "Material texture binding differs from descriptor.");
                var importer = AssetImporter.GetAtPath(entry.Item1.path) as TextureImporter;
                var standalone = importer.GetPlatformTextureSettings("Standalone");
                Require(importer.sRGBTexture == entry.Item4 && importer.textureType == (entry.Item3 ? TextureImporterType.NormalMap : TextureImporterType.Default), "Incorrect texture color space/type.");
                Require(standalone.overridden && standalone.maxTextureSize == spec.maxSize && standalone.format == (entry.Item3 ? TextureImporterFormat.BC5 : TextureImporterFormat.BC7), "Incorrect desktop texture compression.");
            }
        }
    }
}
