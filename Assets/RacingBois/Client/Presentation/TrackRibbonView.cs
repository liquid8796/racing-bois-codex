using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Client.Presentation
{
    /// <summary>Build-once scenery. The shared route remains the sole definition of the rideable road.</summary>
    public sealed class TrackRibbonView : MonoBehaviour
    {
        public Material Asphalt, Shoulder, Landscape, Paint, YellowPaint, Rock, Foliage;
        public GameObject SandstonePrefab, SageScrubPrefab;
        public GameObject RockBPrefab, DryGrassPrefab, GuardrailPrefab, ChevronPrefab, UtilityPolePrefab;
        public Material WireMaterial;
        public Camera ViewCamera;
        private readonly List<Mesh> ownedMeshes = new List<Mesh>();
        private readonly List<Chunk> chunks = new List<Chunk>();
        private readonly List<Vector3> roadClearanceSamples = new List<Vector3>();
        private readonly Dictionary<GameObject, Bounds> sceneryBounds = new Dictionary<GameObject, Bounds>();
        private TrackDefinition track;
        private P08RouteContent routeContent;
        private GameObject generatedRoot;
        public int CourseIndex => track == null ? -1 : track.CourseIndex;
        public int LevelIndex => track == null ? -1 : track.LevelIndex;
        private Transform buildParent;
        private float cullAfter, viewDistance = 650;
        private int quality = 1;
        public int ChunkCount => chunks.Count;
        public int ActiveChunkCount { get; private set; }
        public int RuntimeMeshCount => ownedMeshes.Count;
        public long RuntimeTriangleCount { get; private set; }
        public int AcceptedLargePropCount { get; private set; }
        public int RejectedLargePropCount { get; private set; }
        public float MinimumLargePropRoadClearance { get; private set; } = float.PositiveInfinity;

        public void Build(TrackDefinition definition)
        {
            if (track != null)
            {
                if (ReferenceEquals(track, definition)) return;
                ClearGeometry();
            }
            track = definition ?? throw new ArgumentNullException(nameof(definition));
            generatedRoot = new GameObject("Authored route " + track.CourseIndex + " level " + track.LevelIndex); generatedRoot.transform.SetParent(transform, false);
            if (ViewCamera == null) ViewCamera = Camera.main;
            int length = (int)(track.LengthMillimeters / 1000);
            int sceneryEnd = Mathf.CeilToInt((length + 280) / 160f) * 160 - 80;
            for (int s = -80; s <= sceneryEnd; s += 4) roadClearanceSamples.Add(Point(s));
            for (int start = -80; start < length + 200; start += 160)
            {
                int end = start + 160;
                var chunkObject = new GameObject("Route " + start + "m"); chunkObject.transform.SetParent(generatedRoot.transform, false);
                buildParent = chunkObject.transform;
                chunks.Add(new Chunk(chunkObject, Point(start + 80), 220));
                // Do not change these road/shoulder widths, elevations or the authority's contact surface.
                Strip("Asphalt", start, end, -6.5f, 6.5f, .02f, Asphalt);
                Strip("ShoulderL", start, end, -9, -6.5f, 0, Shoulder);
                Strip("ShoulderR", start, end, 6.5f, 9, 0, Shoulder);
                // The minimum inner bend radius is 139m. Keep the ground ribbon at <=110m to prevent folds.
                Strip("TerrainL", start, end, -110, -9, -.04f, Landscape, true);
                Strip("TerrainR", start, end, 9, 110, -.04f, Landscape, true);
                Strip("EdgeL", start, end, -6.32f, -6.19f, .045f, Paint);
                Strip("EdgeR", start, end, 6.19f, 6.32f, .045f, Paint);
                var lines = new Geometry();
                for (int s = start; s < end; s += 12) AddRibbon(lines, s, Mathf.Min(s + 5, end), -.075f, .075f, .048f, false);
                Publish("Center markings", lines, YellowPaint);
                BuildScenery(start, end);
            }
            buildParent = generatedRoot.transform;
            var finish = new Geometry();
            for (int row = 0; row < 2; row++) for (int col = 0; col < 13; col++)
                if ((row + col) % 2 == 0) AddRibbon(finish, length + row * .6f, length + (row + 1) * .6f, -6.5f + col, -5.5f + col, .05f, false);
            Publish("Finish stripe", finish, Paint);
            BuildHorizon(length);
            UpdateChunkVisibility();
        }

        public void SetSceneryQuality(int index)
        {
            quality = Mathf.Clamp(index, 0, 2); viewDistance = quality == 0 ? 440 : quality == 1 ? 650 : 850;
            cullAfter = 0;
        }

        private void LateUpdate()
        {
            if (ViewCamera == null || Time.unscaledTime < cullAfter) return;
            cullAfter = Time.unscaledTime + .2f; UpdateChunkVisibility();
        }

        private void UpdateChunkVisibility()
        {
            if (ViewCamera == null) { ActiveChunkCount = chunks.Count; return; }
            var cameraPosition = ViewCamera.transform.position; ActiveChunkCount = 0;
            foreach (var chunk in chunks)
            {
                float range = viewDistance + chunk.Radius;
                bool visible = (transform.TransformPoint(chunk.Center) - cameraPosition).sqrMagnitude < range * range;
                if (chunk.Root.activeSelf != visible) chunk.Root.SetActive(visible);
                if (visible) ActiveChunkCount++;
            }
        }

        private void BuildScenery(int start, int end)
        {
            if (routeContent != null && track.CourseIndex != 0) { BuildBiomeScenery(start, end); return; }
            if (SandstonePrefab == null || SageScrubPrefab == null) throw new InvalidOperationException("Missing original canyon rock or sage prefab.");
            var towers = new List<Matrix4x4>(); var shelves = new List<Matrix4x4>();
            // A broad bank and its lower toe share a geological direction. Six upper banks per
            // chunk retain the previous rock budget, while the silhouette reads as canyon walls.
            for (int station = 0; station < 3; station++)
            {
                for (int side = -1; side <= 1; side += 2)
                {
                    int seed = start + station * 53 + side * 19;
                    float s = start + 21 + station * 53 + side * 7 + Hash(seed, 7) * 6;
                    float lateral = side * (32 + Hash(seed, 13) * 9);
                    float yaw = FlatHeading(s).eulerAngles.y + (Hash(seed, 2) - .5f) * 18;
                    var bankScale = new Vector3(5.2f + Hash(seed, 17) * 1.3f,
                        3.0f + Hash(seed, 9) * .4f, 6.6f + Hash(seed, 4) * 1.0f);
                    AddLargeProp(towers, SandstonePrefab, s, lateral, bankScale, yaw, 1.65f);
                    var toeScale = new Vector3(2.4f + Hash(seed, 3) * .7f,
                        1.35f + Hash(seed, 10) * .45f, 5.7f + Hash(seed, 8) * 1.5f);
                    AddLargeProp(shelves, RockBPrefab, s + 8, side * (21 + Hash(seed, 23) * 4), toeScale, yaw + side * 7, .65f);
                }
            }
            // Two low outcrops break the gaps between the six primary groups, not another row of towers.
            for (int i = 0; i < 2; i++)
            {
                int s = start + 45 + i * 77, side = i == 0 ? -1 : 1;
                AddLargeProp(shelves, RockBPrefab, s, side * (16.5f + Hash(s, 21) * 3),
                    new Vector3(1.35f, .65f + Hash(s, 25) * .25f, 2.8f), FlatHeading(s).eulerAngles.y - side * 13, .35f);
            }
            Scatter("Sandstone towers", SandstonePrefab, towers, false, 34);
            Scatter("Sandstone shelves", RockBPrefab, shelves, false, 30);
            var shrubs = new List<Matrix4x4>(); var grass = new List<Matrix4x4>();
            for (int s = start + 4; s < end; s += 18)
            {
                for (int side = -1; side <= 1; side += 2)
                {
                    // Concentrate the existing instance count at gameplay distance instead of
                    // spending most foliage vertices on the far, unreadable hillside.
                    float lateral = side * (10.8f + Hash(s + 50, side) * 8);
                    float shrubScale = .95f + Hash(s, side) * .75f;
                    shrubs.Add(Placement(s, lateral, new Vector3(shrubScale * 1.2f, shrubScale, shrubScale * 1.2f), s * 37));
                    if (DryGrassPrefab == null) continue;
                    for (int cluster = 0; cluster < 3; cluster++)
                    {
                        float gs = s + cluster * 4.5f + Hash(s, cluster) * 2;
                        float d = side * (9.8f + Hash(s + cluster * 11, side + 50) * 6.5f);
                        grass.Add(Placement(gs, d, new Vector3(1.6f, 1.1f, 1.6f) * (.85f + Hash(s, cluster + 3) * .65f), gs * 19));
                    }
                }
            }
            Scatter("Sage clusters", SageScrubPrefab, shrubs, false, 14);
            Scatter("Dry roadside grass", DryGrassPrefab, grass, false, 10);
            BuildRoadFurniture(start, end);
        }

        private void BuildRoadFurniture(int start, int end)
        {
            var rails = new List<Matrix4x4>(); var chevrons = new List<Matrix4x4>(); var poles = new List<Matrix4x4>();
            for (int s = start + 2; s < end; s += 4)
            {
                int curve = track.CurvatureAt((long)s * 1000);
                if (Mathf.Abs(curve) < 3000 || s < 0) continue;
                int outside = curve > 0 ? -1 : 1;
                float lateral = outside * 10.2f;
                rails.Add(Matrix4x4.TRS(Point(s, lateral, TerrainLift(s, lateral) - .04f), Heading(s), Vector3.one));
                // Source arrow points local -X. Reverse the board for a right turn;
                // both authored faces carry valid UVs, so no negative scale is needed.
                if ((s - start - 2) % 28 == 0)
                    chevrons.Add(Matrix4x4.TRS(Point(s, outside * 11.4f, TerrainLift(s, outside * 11.4f) - .04f), Heading(s) * Quaternion.Euler(0, outside > 0 ? 12 : 168, 0), Vector3.one));
            }
            Scatter("Outer bend guardrail", GuardrailPrefab, rails, false, 26);
            Scatter("Bend chevrons", ChevronPrefab, chevrons, false, 15);
            if (UtilityPolePrefab == null) return;
            var wires = new Geometry();
            int firstPole = Mathf.CeilToInt(start / 64f) * 64;
            for (int s = firstPole; s < end; s += 64)
            {
                float lateral = 15.5f;
                var origin = Point(s, lateral, TerrainLift(s, lateral) - .04f);
                poles.Add(Matrix4x4.TRS(origin, FlatHeading(s), Vector3.one));
                for (int line = -1; line <= 1; line++)
                {
                    var a = origin + FlatHeading(s) * new Vector3(line * .9f, 6.68f, 0);
                    var b = Point(s + 64, lateral, TerrainLift(s + 64, lateral) - .04f) + FlatHeading(s + 64) * new Vector3(line * .9f, 6.68f, 0);
                    AddCable(wires, a, b);
                }
            }
            Scatter("Utility line poles", UtilityPolePrefab, poles, false, 28);
            if (WireMaterial != null) Publish("Utility cables", wires, WireMaterial);
        }

        private void BuildHorizon(int length)
        {
            if (routeContent != null && track.CourseIndex != 0) return;
            if (RockBPrefab == null) return;
            var mesas = new List<Matrix4x4>();
            for (int s = 0; s < length + 200; s += 280) for (int side = -1; side <= 1; side += 2)
            {
                float lateral = side * (210 + Hash(s, side) * 100);
                float width = 14 + Hash(s + 11, side) * 10;
                Vector3 p = Point(s, lateral, -17);
                TryAddLargeProp(mesas, RockBPrefab, Matrix4x4.TRS(p, Quaternion.Euler(0, s * .73f, 0),
                    new Vector3(width, 10 + Hash(s, side + 9) * 5, width * .9f)));
            }
            // The concept-led RockB mesh is reused at LOD2 for distant silhouettes; no new production mesh is authored here.
            Scatter("Distant mesas", RockBPrefab, mesas, true, 80);
        }

        private Matrix4x4 Placement(float s, float d, Vector3 scale, float yaw) =>
            Matrix4x4.TRS(Point(s, d, TerrainLift(s, d) - .05f), Quaternion.Euler(0, yaw, 0), scale);

        private void AddLargeProp(List<Matrix4x4> placements, GameObject prefab, float s, float d, Vector3 scale, float yaw, float sink)
        {
            if (prefab == null) return;
            // Reject against the entire road, including another arm of a bend. A rejected near
            // placement can move outward twice; it must never be pushed into the rideable corridor.
            for (int attempt = 0; attempt < 3; attempt++)
            {
                float lateral = d + Mathf.Sign(d) * attempt * 8;
                var matrix = GroundedPlacement(prefab, s, lateral, scale, yaw, sink);
                if (TryAddLargeProp(placements, prefab, matrix, false)) return;
            }
            RejectedLargePropCount++;
        }

        private Matrix4x4 GroundedPlacement(GameObject prefab, float s, float d, Vector3 scale, float yaw, float sink)
        {
            var bounds = SceneryBounds(prefab);
            var rotation = Quaternion.Euler(0, yaw, 0);
            Vector3 position = Point(s, d);
            float ground = float.PositiveInfinity;
            // A centre-height placement leaves the roadward underside hanging above a slope.
            // Sample the actual rotated footprint, including its interior, and bury its base
            // beneath the lowest surface. This runs only while constructing the static batches.
            for (int x = 0; x <= 4; x++) for (int z = 0; z <= 4; z++)
            {
                Vector3 offset = rotation * new Vector3(Mathf.Lerp(bounds.min.x, bounds.max.x, x / 4f) * scale.x,
                    0, Mathf.Lerp(bounds.min.z, bounds.max.z, z / 4f) * scale.z);
                Vector3 point = position + offset;
                float sampleS = s, sampleD = d;
                // Invert the curved road coordinates; a simple tangent projection is inaccurate
                // on the inner bank because lateral offset shortens the local arc length.
                for (int iteration = 0; iteration < 4; iteration++)
                {
                    var sample = track.Sample((long)(sampleS * 1000));
                    float dx = point.x - sample.CenterX, dz = point.z - sample.CenterZ;
                    sampleD = dx * sample.ForwardZ - dz * sample.ForwardX;
                    float along = dx * sample.ForwardX + dz * sample.ForwardZ;
                    float arcScale = 1 - sample.CurvatureMicroRadiansPerMeter * .000001f * sampleD;
                    sampleS += along / Mathf.Max(.25f, arcScale);
                }
                var finalSample = track.Sample((long)(sampleS * 1000));
                sampleD = (point.x - finalSample.CenterX) * finalSample.ForwardZ - (point.z - finalSample.CenterZ) * finalSample.ForwardX;
                ground = Mathf.Min(ground, finalSample.CenterY + TerrainLift(sampleS, sampleD) - .04f);
            }
            position.y = ground - bounds.min.y * scale.y - sink;
            return Matrix4x4.TRS(position, rotation, scale);
        }

        private bool TryAddLargeProp(List<Matrix4x4> placements, GameObject prefab, Matrix4x4 matrix, bool countRejection = true)
        {
            Bounds bounds = SceneryBounds(prefab);
            var corners = new Vector2[4];
            for (int i = 0; i < 4; i++)
            {
                var p = matrix.MultiplyPoint3x4(new Vector3(i == 0 || i == 3 ? bounds.min.x : bounds.max.x,
                    0, i < 2 ? bounds.min.z : bounds.max.z));
                corners[i] = new Vector2(p.x, p.z);
            }
            float minimum = float.PositiveInfinity;
            for (int i = 1; i < roadClearanceSamples.Count; i++)
            {
                Vector3 previous = roadClearanceSamples[i - 1], current = roadClearanceSamples[i];
                var a = new Vector2(previous.x, previous.z); var b = new Vector2(current.x, current.z);
                if (InsideFootprint(a, corners) || InsideFootprint(b, corners)) { minimum = 0; break; }
                for (int edge = 0; edge < 4; edge++) minimum = Mathf.Min(minimum,
                    SegmentDistanceSquared(a, b, corners[edge], corners[(edge + 1) % 4]));
                if (minimum < 10.25f * 10.25f) break;
            }
            // Road plus shoulder is 9 m each side. The additional .25 m conservatively covers
            // the 4 m sampling chord; leave at least a further metre before any rock bounds.
            float clearance = Mathf.Sqrt(minimum) - 9.25f;
            if (clearance < 1)
            {
                if (countRejection) RejectedLargePropCount++;
                return false;
            }
            placements.Add(matrix); AcceptedLargePropCount++;
            MinimumLargePropRoadClearance = Mathf.Min(MinimumLargePropRoadClearance, clearance);
            return true;
        }

        private Bounds SceneryBounds(GameObject prefab)
        {
            if (sceneryBounds.TryGetValue(prefab, out var bounds)) return bounds;
            bool first = true;
            foreach (var lod in prefab.GetComponent<LODGroup>().GetLODs()) foreach (var renderer in lod.renderers)
            {
                var meshBounds = renderer.GetComponent<MeshFilter>().sharedMesh.bounds;
                var basis = prefab.transform.worldToLocalMatrix * renderer.transform.localToWorldMatrix;
                for (int i = 0; i < 8; i++)
                {
                    var p = basis.MultiplyPoint3x4(new Vector3((i & 1) == 0 ? meshBounds.min.x : meshBounds.max.x,
                        (i & 2) == 0 ? meshBounds.min.y : meshBounds.max.y, (i & 4) == 0 ? meshBounds.min.z : meshBounds.max.z));
                    if (first) { bounds = new Bounds(p, Vector3.zero); first = false; } else bounds.Encapsulate(p);
                }
            }
            sceneryBounds.Add(prefab, bounds); return bounds;
        }

        private static bool InsideFootprint(Vector2 point, Vector2[] corners)
        {
            float sign = 0;
            for (int i = 0; i < 4; i++)
            {
                float cross = Cross(corners[(i + 1) % 4] - corners[i], point - corners[i]);
                if (Mathf.Abs(cross) < .0001f) continue;
                if (sign != 0 && sign * cross < 0) return false;
                sign = cross;
            }
            return true;
        }
        private static float SegmentDistanceSquared(Vector2 a, Vector2 b, Vector2 c, Vector2 d)
        {
            Vector2 ab = b - a, cd = d - c; float denominator = Cross(ab, cd);
            if (Mathf.Abs(denominator) > .00001f)
            {
                float t = Cross(c - a, cd) / denominator, u = Cross(c - a, ab) / denominator;
                if (t >= 0 && t <= 1 && u >= 0 && u <= 1) return 0;
            }
            return Mathf.Min(Mathf.Min(PointSegmentDistanceSquared(a, c, d), PointSegmentDistanceSquared(b, c, d)),
                Mathf.Min(PointSegmentDistanceSquared(c, a, b), PointSegmentDistanceSquared(d, a, b)));
        }
        private static float PointSegmentDistanceSquared(Vector2 p, Vector2 a, Vector2 b)
        {
            Vector2 delta = b - a; float length = delta.sqrMagnitude;
            return (p - a - delta * (length < .00001f ? 0 : Mathf.Clamp01(Vector2.Dot(p - a, delta) / length))).sqrMagnitude;
        }
        private static float Cross(Vector2 a, Vector2 b) => a.x * b.y - a.y * b.x;

        public Vector3 Point(float meters, float lateral = 0, float height = 0)
        {
            var sample = track.Sample((long)(meters * 1000));
            return new Vector3(sample.CenterX + sample.ForwardZ * lateral, sample.CenterY + height, sample.CenterZ - sample.ForwardX * lateral);
        }
        public Quaternion Heading(float meters)
        {
            var sample = track.Sample((long)(meters * 1000));
            return Quaternion.LookRotation(new Vector3(sample.ForwardX, sample.GradePermille / 1000f, sample.ForwardZ).normalized, Vector3.up);
        }
        private Quaternion FlatHeading(float meters)
        {
            var sample = track.Sample((long)(meters * 1000));
            return Quaternion.LookRotation(new Vector3(sample.ForwardX, 0, sample.ForwardZ), Vector3.up);
        }
        private static float Hash(int a, int b) { uint v = unchecked((uint)(a * 374761393 + b * 668265263)); v = (v ^ (v >> 13)) * 1274126177; return (v & 65535) / 65535f; }
        private float TerrainLift(float s, float d)
        {
            float distance = Mathf.Max(0, Mathf.Abs(d) - 10), side = d < 0 ? -1 : 1;
            if (track != null && track.CourseIndex == 1) return Mathf.Min(.18f, distance * .02f);
            if (track != null && track.CourseIndex == 2) return d < 0 ? -distance * .25f : distance * (.16f + .07f * Mathf.Sin(s * .013f));
            if (track != null && track.CourseIndex == 3) return d > 0 ? -distance * .28f : distance * .11f + Mathf.Sin(s * .013f) * Mathf.Min(2,distance*.1f);
            if (track != null && track.CourseIndex == 4) return Mathf.Sin(s * .012f + d * .026f) * Mathf.Min(2.5f,distance*.06f) + distance*.009f;
            float ridge = .45f + .55f * Mathf.Pow(Mathf.Sin(s * .0105f + side * 1.9f), 2);
            float terraces = Mathf.Sin(distance * .135f + Mathf.Sin(s * .018f) * 1.8f) * .5f + .5f;
            float ripple = Mathf.Sin(s * .046f + d * .089f) * Mathf.Sin(s * .017f - d * .051f);
            return distance * (.038f + ridge * .135f) + Mathf.SmoothStep(0, 1, distance / 18) * (terraces * 2.6f + ripple * 1.1f);
        }
        private void Strip(string name, float from, float to, float left, float right, float lift, Material material, bool terrain = false)
        { var geometry = new Geometry(); AddRibbon(geometry, from, to, left, right, lift, terrain); Publish(name, geometry, material); }
        private void AddRibbon(Geometry geometry, float from, float to, float left, float right, float lift, bool terrain)
        {
            int spans = Mathf.Max(1, Mathf.CeilToInt((to - from) / 4)), across = terrain ? 12 : 1, offset = geometry.Vertices.Count;
            for (int i = 0; i <= spans; i++)
            {
                float s = Mathf.Lerp(from, to, i / (float)spans);
                for (int j = 0; j <= across; j++)
                {
                    float d = Mathf.Lerp(left, right, j / (float)across);
                    geometry.Vertices.Add(Point(s, d, lift + (terrain ? TerrainLift(s, d) : 0)));
                    geometry.Uv.Add(new Vector2(d * .18f, s * .15f));
                }
            }
            for (int i = 0; i < spans; i++) for (int j = 0; j < across; j++)
            {
                int a = offset + i * (across + 1) + j, b = a + 1, c = a + across + 1, d = c + 1;
                geometry.Triangles.Add(a); geometry.Triangles.Add(c); geometry.Triangles.Add(b);
                geometry.Triangles.Add(b); geometry.Triangles.Add(c); geometry.Triangles.Add(d);
            }
        }
        private static void AddCable(Geometry g, Vector3 from, Vector3 to)
        {
            int offset = g.Vertices.Count;
            for (int i = 0; i <= 12; i++)
            {
                float t = i / 12f; Vector3 center = Vector3.Lerp(from, to, t) - Vector3.up * (4 * t * (1 - t) * 1.35f);
                Vector3 forward = (to - from).normalized, right = Vector3.Cross(forward, Vector3.up).normalized, up = Vector3.Cross(right, forward);
                for (int side = 0; side < 3; side++)
                {
                    float a = side * Mathf.PI * 2 / 3;
                    g.Vertices.Add(center + (right * Mathf.Cos(a) + up * Mathf.Sin(a)) * .025f);
                    // Dark painted tile in the original Roadside atlas.
                    g.Uv.Add(new Vector2(.80f + side * .035f, .06f + t * .12f));
                    if (i == 12) continue;
                    int p = offset + i * 3 + side, q = offset + i * 3 + (side + 1) % 3;
                    g.Triangles.Add(p); g.Triangles.Add(q); g.Triangles.Add(p + 3);
                    g.Triangles.Add(q); g.Triangles.Add(q + 3); g.Triangles.Add(p + 3);
                }
            }
        }
        private void Scatter(string label, GameObject prefab, List<Matrix4x4> placements, bool horizon, float lodSize)
        {
            if (placements.Count == 0) return;
            if (prefab == null)
            {
                if (label == "Sandstone towers" || label == "Sage clusters") throw new InvalidOperationException("Missing original canyon prefab: " + label);
                return;
            }
            var sources = prefab.GetComponent<LODGroup>().GetLODs();
            var parent = new GameObject(label + " batch"); parent.transform.SetParent(buildParent, false); parent.isStatic = true;
            var lods = new LOD[horizon ? 1 : 3];
            for (int level = 0; level < lods.Length; level++)
            {
                int sourceLevel = horizon ? 2 : level;
                var source = sources[sourceLevel].renderers[0];
                var combinations = new CombineInstance[placements.Count];
                Matrix4x4 sourceBasis = prefab.transform.worldToLocalMatrix * source.transform.localToWorldMatrix;
                for (int i = 0; i < placements.Count; i++) combinations[i] = new CombineInstance
                { mesh = source.GetComponent<MeshFilter>().sharedMesh, transform = placements[i] * sourceBasis };
                var mesh = new Mesh { name = "RB_" + label + "_L" + sourceLevel, indexFormat = IndexFormat.UInt32 };
                mesh.CombineMeshes(combinations, true, true, false); mesh.RecalculateBounds(); TrackMesh(mesh); mesh.UploadMeshData(true);
                var obj = new GameObject("LOD" + sourceLevel); obj.transform.SetParent(parent.transform, false); obj.isStatic = true;
                obj.AddComponent<MeshFilter>().sharedMesh = mesh;
                var renderer = obj.AddComponent<MeshRenderer>(); renderer.sharedMaterial = source.sharedMaterial;
                bool castsShadow = !horizon && (routeContent != null || label == "Sandstone towers" || label == "Sandstone shelves" || label == "Utility line poles" || label == "Outer bend guardrail");
                renderer.shadowCastingMode = castsShadow ? ShadowCastingMode.On : ShadowCastingMode.Off; renderer.receiveShadows = !horizon;
                renderer.lightProbeUsage = LightProbeUsage.Off; renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;
                lods[level] = new LOD(horizon ? .001f : level == 0 ? .23f : level == 1 ? .07f : .009f, new Renderer[] { renderer });
            }
            var group = parent.AddComponent<LODGroup>(); group.SetLODs(lods); group.RecalculateBounds();
            if (!horizon) group.size = lodSize;
        }
        private void Publish(string label, Geometry geometry, Material material)
        {
            if (geometry.Vertices.Count == 0) return;
            var mesh = new Mesh { name = "RB_" + label, indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(geometry.Vertices); mesh.SetUVs(0, geometry.Uv); mesh.SetTriangles(geometry.Triangles, 0);
            mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds(); TrackMesh(mesh); mesh.UploadMeshData(true);
            var obj = new GameObject(label); obj.transform.SetParent(buildParent, false); obj.isStatic = true;
            obj.AddComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = obj.AddComponent<MeshRenderer>(); renderer.sharedMaterial = material;
            renderer.shadowCastingMode = ShadowCastingMode.Off; renderer.receiveShadows = true;
            renderer.lightProbeUsage = LightProbeUsage.Off; renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;
        }
        private void TrackMesh(Mesh mesh) { ownedMeshes.Add(mesh); RuntimeTriangleCount += (long)mesh.GetIndexCount(0) / 3; }
        public void ClearContent()
        {
            ClearGeometry(); routeContent = null;
            Asphalt = Shoulder = Landscape = Paint = YellowPaint = Rock = Foliage = WireMaterial = null;
            SandstonePrefab = SageScrubPrefab = RockBPrefab = DryGrassPrefab = GuardrailPrefab = ChevronPrefab = UtilityPolePrefab = null;
        }
        private void ClearGeometry()
        {
            if (generatedRoot != null) { generatedRoot.SetActive(false); DestroyOwned(generatedRoot); generatedRoot = null; }
            foreach (var mesh in ownedMeshes) if (mesh != null) DestroyOwned(mesh);
            ownedMeshes.Clear(); chunks.Clear(); sceneryBounds.Clear(); roadClearanceSamples.Clear(); track = null;
            RuntimeTriangleCount = 0; ActiveChunkCount = AcceptedLargePropCount = RejectedLargePropCount = 0;
            MinimumLargePropRoadClearance = float.PositiveInfinity;
        }
        public void ApplyContent(P08RouteContent content, int level)
        {
            content.Validate(content.CourseIndex); ClearGeometry(); routeContent = content;
            Asphalt = content.Asphalt; Shoulder = content.Shoulder; Landscape = content.Landscape; Paint = content.Paint; YellowPaint = content.YellowPaint; WireMaterial = content.Wire;
            GuardrailPrefab = content.Guardrail; ChevronPrefab = content.Chevron; UtilityPolePrefab = content.UtilityPole;
            if (content.CourseIndex == 0)
            {
                SandstonePrefab = content.Props[0]; RockBPrefab = content.Props[1]; SageScrubPrefab = content.Props[2]; DryGrassPrefab = content.Props[3];
                if (GuardrailPrefab == null) GuardrailPrefab = content.Props[4]; if (ChevronPrefab == null) ChevronPrefab = content.Props[5];
            }
            Build(TrackDefinition.ForCourse(content.CourseIndex,level));
        }
        private void BuildBiomeScenery(int start, int end)
        {
            int course = track.CourseIndex;
            for (int index = 0; index < 6; index++)
            {
                var prefab = routeContent.Props[index]; var placements = new List<Matrix4x4>();
                int spacing; float lateral;
                if (course == 1) { spacing = index < 2 ? 72 : index == 2 ? 40 : index == 3 ? 180 : 300; lateral = index < 2 ? 25 : index == 2 ? 12 : index == 3 ? 15 : 48; }
                else if (course == 2) { spacing = index == 0 ? 22 : index == 1 ? 48 : index == 2 ? 24 : index == 3 ? 260 : index == 4 ? 32 : 640; lateral = index == 0 ? 22 : index == 1 ? 32 : index == 2 ? 12.5f : index == 3 ? 43 : index == 4 ? 11.8f : 0; }
                else if (course == 3) { spacing = index == 0 ? 38 : index == 1 ? 270 : index == 2 ? 640 : index == 3 ? 160 : index == 4 ? 52 : 18; lateral = index == 0 ? 20 : index == 1 ? 32 : index == 2 ? 85 : index == 3 ? 24 : index == 4 ? 29 : 14; }
                else { spacing = index == 0 ? 24 : index == 1 ? 340 : index == 2 ? 360 : index == 3 ? 14 : index == 4 ? 70 : 260; lateral = index == 0 ? 24 : index == 1 ? 48 : index == 2 ? 56 : index == 3 ? 12.5f : index == 4 ? 32 : 25; }
                int first = Mathf.CeilToInt((start + index * 11f) / spacing) * spacing - index * 11;
                for (int station = first; station < end; station += spacing)
                {
                    if (station < 0 || station > track.LengthMillimeters / 1000) continue;
                    if (course == 2 && index == 5)
                    {
                        // Authored 14.45m clear opening is widened to keep posts outside the 18m road/shoulder corridor.
                        placements.Add(Matrix4x4.TRS(Point(station), Heading(station), new Vector3(1.55f,1,1))); continue;
                    }
                    bool both = index == 0 || course == 4 && index == 3 || course == 2 && (index == 2 || index == 4);
                    int startSide = both ? -1 : ((index & 1) == 0 ? -1 : 1);
                    for (int side = startSide; side <= 1; side += 2)
                    {
                        float d = side * (lateral + (index == 0 ? Hash(station,index) * 8 : 0));
                        float yaw = FlatHeading(station).eulerAngles.y + (side > 0 ? -90 : 90);
                        if (index == 0 || course == 2 && index == 1 || course == 3 && index > 3) yaw += Hash(station,17) * 360;
                        float scale = index == 0 ? .9f + Hash(station,index) * .25f : 1;
                        AddLargeProp(placements,prefab,station,d,Vector3.one*scale,yaw,.02f);
                        if (!both) break;
                    }
                }
                Scatter("Biome " + course + " prop " + index,prefab,placements,false,index == 0 ? 22 : 34);
            }
            BuildRoadFurniture(start,end);
            if (course == 3 && routeContent.Water != null)
            {
                // Visual ocean is outside the authoritative corridor and never supplies contacts.
                var ocean=new Geometry();AddRibbon(ocean,start,end,90,210,0,false);
                for(int i=0;i<ocean.Vertices.Count;i++){var vertex=ocean.Vertices[i];vertex.y=-25;ocean.Vertices[i]=vertex;}
                Publish("Ocean",ocean,routeContent.Water);
            }
        }
        private void OnDestroy() { ClearGeometry(); }
        private static void DestroyOwned(UnityEngine.Object value)
        {
            if(value==null)return;
            if(UnityEngine.Application.isPlaying)UnityEngine.Object.Destroy(value);else UnityEngine.Object.DestroyImmediate(value);
        }
        private sealed class Chunk
        {
            public readonly GameObject Root; public readonly Vector3 Center; public readonly float Radius;
            public Chunk(GameObject root, Vector3 center, float radius) { Root = root; Center = center; Radius = radius; }
        }
        private sealed class Geometry
        {
            public readonly List<Vector3> Vertices = new List<Vector3>();
            public readonly List<Vector2> Uv = new List<Vector2>();
            public readonly List<int> Triangles = new List<int>();
        }
    }
}
