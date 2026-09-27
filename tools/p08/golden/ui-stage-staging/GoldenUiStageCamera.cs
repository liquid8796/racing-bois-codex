#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    internal static class GoldenUiStageCamera
    {
        /// <summary>Measure the actual posed LOD0 mesh, not its generous animation culling envelope.</summary>
        internal static Bounds Measure(params GameObject[] subjects)
        {
            var selected = new HashSet<Renderer>();
            foreach (var subject in subjects)
            {
                if (subject == null || !subject.activeInHierarchy) continue;
                var excluded = new HashSet<Renderer>();
                foreach (var group in subject.GetComponentsInChildren<LODGroup>(true))
                {
                    var lods = group.GetLODs();
                    for (int i = 1; i < lods.Length; i++) foreach (var renderer in lods[i].renderers) excluded.Add(renderer);
                }
                foreach (var renderer in subject.GetComponentsInChildren<Renderer>(false))
                    if (renderer.enabled && !excluded.Contains(renderer)) selected.Add(renderer);
            }
            var bounds = new Bounds(); bool initialized = false;
            var baked = new Mesh();
            try
            {
                foreach (var renderer in selected)
                {
                    if (renderer is SkinnedMeshRenderer skin)
                    {
                        skin.BakeMesh(baked, false);
                        foreach (var vertex in baked.vertices) Add(ref bounds, ref initialized, skin.transform.TransformPoint(vertex));
                    }
                    else
                    {
                        var filter = renderer.GetComponent<MeshFilter>();
                        if (filter == null || filter.sharedMesh == null) continue;
                        foreach (var corner in Corners(filter.sharedMesh.bounds)) Add(ref bounds, ref initialized, renderer.transform.TransformPoint(corner));
                    }
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(baked); }
            if (!initialized || bounds.size.sqrMagnitude < .01f) throw new InvalidOperationException("Candidate has no measurable LOD0 geometry.");
            return bounds;
        }

        /// <summary>Fit real geometry to the measured target rect while preserving a full-screen UI camera.</summary>
        internal static Rect Frame(Camera camera, Bounds bounds, Vector3 direction, float fieldOfView, Rect target)
        {
            if (!float.IsFinite(direction.sqrMagnitude) || !float.IsFinite(fieldOfView) || fieldOfView < 10 || fieldOfView > 90 ||
                !float.IsFinite(target.x + target.y + target.width + target.height) || direction.sqrMagnitude < .01f || target.width <= 0 || target.height <= 0 ||
                target.xMin < 0 || target.yMin < 0 || target.xMax > 1 || target.yMax > 1)
                throw new ArgumentException("Invalid camera composition.");
            camera.orthographic = false; camera.fieldOfView = fieldOfView; camera.ResetAspect();
            camera.nearClipPlane = .03f; camera.farClipPlane = 2200;
            direction.Normalize(); camera.transform.rotation = Quaternion.LookRotation(-direction, Vector3.up);
            float low = bounds.extents.magnitude + .1f, high = low * 30;
            for (int i = 0; i < 36; i++)
            {
                float distance = (low + high) * .5f;
                camera.transform.position = bounds.center + direction * distance; camera.ResetProjectionMatrix();
                Rect projected = Project(camera, bounds);
                if (projected.width > target.width || projected.height > target.height) low = distance; else high = distance;
            }
            camera.transform.position = bounds.center + direction * high; camera.ResetProjectionMatrix();
            Rect measured = Project(camera, bounds);
            var matrix = camera.projectionMatrix;
            matrix.m02 += 2 * (measured.center.x - target.center.x);
            matrix.m12 += 2 * (measured.center.y - target.center.y);
            camera.projectionMatrix = matrix;
            return Project(camera, bounds);
        }

        private static Rect Project(Camera camera, Bounds bounds)
        {
            var min = new Vector2(float.PositiveInfinity, float.PositiveInfinity);
            var max = new Vector2(float.NegativeInfinity, float.NegativeInfinity);
            foreach (var corner in Corners(bounds))
            {
                var p = camera.WorldToViewportPoint(corner);
                if (p.z <= camera.nearClipPlane) throw new InvalidOperationException("Camera is inside the candidate bounds.");
                min = Vector2.Min(min, new Vector2(p.x, p.y)); max = Vector2.Max(max, new Vector2(p.x, p.y));
            }
            return Rect.MinMaxRect(min.x, min.y, max.x, max.y);
        }
        private static void Add(ref Bounds bounds, ref bool initialized, Vector3 point)
        {
            if (!float.IsFinite(point.x) || !float.IsFinite(point.y) || !float.IsFinite(point.z)) throw new InvalidOperationException("Non-finite candidate geometry.");
            if (initialized) bounds.Encapsulate(point); else { bounds = new Bounds(point, Vector3.zero); initialized = true; }
        }
        private static IEnumerable<Vector3> Corners(Bounds bounds)
        {
            for (int i = 0; i < 8; i++) yield return bounds.center + Vector3.Scale(bounds.extents,
                new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
        }
    }
}
#endif
