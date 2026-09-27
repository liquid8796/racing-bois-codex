using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        /// <summary>Opt-in bind restoration for FBX imports whose default take differs from the mesh's authored rest pose.</summary>
        private static void RestoreDeclaredRestPose(GameObject model, AssetSpec spec)
        {
            if (string.IsNullOrEmpty(spec.restPose) || spec.restPose == "file") return;
            Require(spec.kind == "rider" && spec.restPose == "bind", "Unsupported rest-pose policy.");
            var targets = new Dictionary<Transform, Matrix4x4>();
            foreach (var skin in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var mesh = skin.sharedMesh;
                Require(mesh != null && mesh.bindposes.Length == skin.bones.Length && skin.bones.Length > 0,
                    "Bind restoration needs a complete skin/bone mapping.");
                var bindPoses = mesh.bindposes;
                for (int i = 0; i < skin.bones.Length; i++)
                {
                    var bone = skin.bones[i];
                    Require(bone != null && bone.IsChildOf(model.transform), "Bind bone is outside the imported hierarchy.");
                    var target = skin.transform.localToWorldMatrix * bindPoses[i].inverse;
                    Require(BindMatrixFinite(target) && Mathf.Abs(target.determinant) > .0001f, "Singular or invalid bind matrix.");
                    if (targets.TryGetValue(bone, out var previous))
                        Require(BindMatrixMatches(previous, target), "Skins disagree about the bind pose of " + bone.name);
                    else targets.Add(bone, target);
                }
            }
            Require(targets.Count >= 15, "Bind restoration requires the declared rider skeleton.");
            // Parents must be restored before deriving a child's new local matrix.
            foreach (var bone in targets.Keys.OrderBy(BindDepth))
            {
                Matrix4x4 local = bone.parent.worldToLocalMatrix * targets[bone];
                var position = (Vector3)local.GetColumn(3);
                var rotation = local.rotation;
                var scale = local.lossyScale;
                Require(Finite(position) && Finite(scale) && scale.x > 0 && scale.y > 0 && scale.z > 0
                    && BindMatrixMatches(Matrix4x4.TRS(position, rotation, scale), local),
                    "Bind pose contains unsupported shear/reflection: " + bone.name);
                bone.localPosition = position; bone.localRotation = rotation; bone.localScale = scale;
                Require(BindMatrixMatches(bone.localToWorldMatrix, targets[bone]), "Bind pose restoration failed: " + bone.name);
            }
        }

        private static int BindDepth(Transform bone)
        { int depth = 0; while (bone.parent != null) { depth++; bone = bone.parent; } return depth; }

        private static bool BindMatrixFinite(Matrix4x4 matrix)
        {
            for (int i = 0; i < 16; i++) if (float.IsNaN(matrix[i]) || float.IsInfinity(matrix[i])) return false;
            return true;
        }

        private static bool BindMatrixMatches(Matrix4x4 left, Matrix4x4 right)
        {
            if (!BindMatrixFinite(left) || !BindMatrixFinite(right)) return false;
            for (int i = 0; i < 16; i++)
                if (Mathf.Abs(left[i] - right[i]) > .0002f + Mathf.Abs(right[i]) * .00001f) return false;
            return true;
        }
    }
}
