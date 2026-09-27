#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    internal static class GoldenUiStageCamera
    {
        internal sealed class Geometry
        {
            internal Bounds Bounds;
            internal Vector3[] Positions;
        }
        /// <summary>Measure the actual posed LOD0 mesh, not its generous animation culling envelope.</summary>
        internal static Geometry Measure(params GameObject[] subjects)
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
            var bounds = new Bounds(); bool initialized = false; var positions = new List<Vector3>();
            var baked = new Mesh();
            try
            {
                foreach (var renderer in selected)
                {
                    if (renderer is SkinnedMeshRenderer skin)
                    {
                        skin.BakeMesh(baked, false);
                        foreach (var vertex in baked.vertices) Add(positions, ref bounds, ref initialized, skin.transform.TransformPoint(vertex));
                    }
                    else
                    {
                        var filter = renderer.GetComponent<MeshFilter>();
                        if (filter == null || filter.sharedMesh == null) continue;
                        foreach (var vertex in filter.sharedMesh.vertices) Add(positions, ref bounds, ref initialized, renderer.transform.TransformPoint(vertex));
                    }
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(baked); }
            if (!initialized || bounds.size.sqrMagnitude < .01f) throw new InvalidOperationException("Candidate has no measurable LOD0 geometry.");
            return new Geometry { Bounds = bounds, Positions = positions.ToArray() };
        }

        /// <summary>Fit real geometry to the measured target rect while preserving a full-screen UI camera.</summary>
        internal static Rect Frame(Camera camera, Geometry geometry, Vector3 direction, float fieldOfView, Rect target)
        {
            if (geometry == null || geometry.Positions == null || geometry.Positions.Length == 0) throw new ArgumentException("Measured mesh geometry is required.");
            var bounds = geometry.Bounds;
            if (!float.IsFinite(direction.sqrMagnitude) || !float.IsFinite(fieldOfView) || fieldOfView < 10 || fieldOfView > 90 ||
                !float.IsFinite(target.x + target.y + target.width + target.height) || direction.sqrMagnitude < .01f || target.width <= 0 || target.height <= 0 ||
                target.xMin < 0 || target.yMin < 0 || target.xMax > 1 || target.yMax > 1)
                throw new ArgumentException("Invalid camera composition.");
            camera.orthographic = false; camera.fieldOfView = fieldOfView; camera.ResetAspect();
            camera.nearClipPlane = .03f; camera.farClipPlane = 2200;
            direction.Normalize(); camera.transform.rotation = Quaternion.LookRotation(-direction, Vector3.up);
            // Transform vertices once. The fit then uses managed perspective math
            // rather than millions of engine calls or projecting empty AABB corners.
            var inverse = Quaternion.Inverse(camera.transform.rotation);
            var viewPoints = new Vector3[geometry.Positions.Length];
            for (int i = 0; i < viewPoints.Length; i++) viewPoints[i] = inverse * (geometry.Positions[i] - bounds.center);
            float verticalScale = 1 / Mathf.Tan(fieldOfView * Mathf.Deg2Rad * .5f);
            float horizontalScale = verticalScale / camera.aspect;
            float low = bounds.extents.magnitude + .1f, high = low * 30;
            for (int i = 0; i < 36; i++)
            {
                float distance = (low + high) * .5f;
                Rect projected = Project(viewPoints, distance, horizontalScale, verticalScale, camera.nearClipPlane);
                if (projected.width > target.width || projected.height > target.height) low = distance; else high = distance;
            }
            camera.transform.position = bounds.center + direction * high; camera.ResetProjectionMatrix();
            Rect measured = Project(viewPoints, high, horizontalScale, verticalScale, camera.nearClipPlane);
            var matrix = camera.projectionMatrix;
            matrix.m02 += 2 * (measured.center.x - target.center.x);
            matrix.m12 += 2 * (measured.center.y - target.center.y);
            camera.projectionMatrix = matrix;
            return new Rect(target.center - measured.size * .5f, measured.size);
        }

        private static Rect Project(Vector3[] points, float distance, float horizontalScale, float verticalScale, float near)
        {
            var min = new Vector2(float.PositiveInfinity, float.PositiveInfinity);
            var max = new Vector2(float.NegativeInfinity, float.NegativeInfinity);
            foreach (var point in points)
            {
                float z = point.z + distance;
                if (z <= near) throw new InvalidOperationException("Camera is inside the candidate geometry.");
                float x = .5f + .5f * horizontalScale * point.x / z;
                float y = .5f + .5f * verticalScale * point.y / z;
                min.x = Math.Min(min.x, x); min.y = Math.Min(min.y, y);
                max.x = Math.Max(max.x, x); max.y = Math.Max(max.y, y);
            }
            return Rect.MinMaxRect(min.x, min.y, max.x, max.y);
        }
        private static void Add(List<Vector3> positions, ref Bounds bounds, ref bool initialized, Vector3 point)
        {
            if (!float.IsFinite(point.x) || !float.IsFinite(point.y) || !float.IsFinite(point.z)) throw new InvalidOperationException("Non-finite candidate geometry.");
            if (initialized) bounds.Encapsulate(point); else { bounds = new Bounds(point, Vector3.zero); initialized = true; }
            positions.Add(point);
        }
    }
}
#endif
