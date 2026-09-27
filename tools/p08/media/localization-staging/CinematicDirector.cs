using System;
using System.Collections.Generic;
using RacingBois.Client.Application;
using UnityEngine;

namespace RacingBois.Client.Presentation
{
    /// <summary>Optional presentation on the existing authored road. Never writes race or wallet state.</summary>
    [DefaultExecutionOrder(500)]
    [DisallowMultipleComponent]
    public sealed class CinematicDirector : MonoBehaviour
    {
        public event Action<CinematicDefinition, bool> Completed;
        public event Action<string> MusicRequested;
        public event Action Changed;
        public bool IsPlaying { get; private set; }
        public bool ReducedMotion { get; set; }
        public CinematicDefinition Current { get; private set; }
        public CinematicBeat CurrentBeat { get; private set; }
        public float ElapsedSeconds { get; private set; }
        public string LastError { get; private set; } = "";
        public string LastErrorCode { get; private set; } = "";
        public int OwnedActorCount => actors.Count;
        public int OwnedPropCount => props.Count;
        private const float AnchorMeters = 22;
        private RaceStageView stage;
        private GameObject root;
        private readonly Dictionary<int, CinematicActorView> actors = new Dictionary<int, CinematicActorView>(4);
        private readonly List<GameObject> props = new List<GameObject>(3);
        private readonly List<RendererState> hidden = new List<RendererState>();
        private Vector3 cameraPosition;
        private Quaternion cameraRotation;
        private float cameraFov;
        private bool cameraCaptured;
        private int beatIndex = -1;
        private float startTime;

        private readonly struct RendererState
        {
            public readonly Renderer Renderer; public readonly bool ForceOff;
            public RendererState(Renderer renderer) { Renderer = renderer; ForceOff = renderer.forceRenderingOff; }
        }
        public void Initialize(RaceStageView presentation) { stage = presentation; }
        public bool StartPlayback(CinematicDefinition definition)
        {
            Stop(true); LastError = ""; LastErrorCode = "";
            if (definition == null || stage == null || stage.Road == null || stage.ViewCamera == null || ContentRegistry.Actors == null || ContentRegistry.Route == null)
            { LastErrorCode = "content-unavailable"; LastError = "Nội dung phim chưa sẵn sàng. Hãy tải một đường đua trước."; Changed?.Invoke(); return false; }
            try
            {
                var content = ContentRegistry.Actors;
                if (definition.BikeIndex < 0 || definition.BikeIndex >= ContentRegistry.Bikes.Count || definition.CharacterIndex < 0 || definition.CharacterIndex >= ContentRegistry.Riders.Count)
                    throw new InvalidOperationException("Cinematic actor identity is unavailable.");
                root = new GameObject("Cinematic stage / " + definition.Id); root.transform.SetParent(transform, false);
                int mask = 0; foreach (var beat in definition.Beats) mask |= beat.ParticipantMask;
                for (int slot = 0; slot < 4; slot++)
                {
                    if ((mask & (1 << slot)) == 0) continue;
                    int bike = (definition.BikeIndex + (slot == 1 ? 3 : 0)) % ContentRegistry.Bikes.Count;
                    int rider = (definition.CharacterIndex + slot) % ContentRegistry.Riders.Count;
                    var bikePrefab = slot == 2 ? content.PoliceBike : ContentRegistry.Bikes[bike];
                    var riderPrefab = slot == 2 ? content.PoliceRider : ContentRegistry.Riders[rider];
                    actors.Add(slot, new CinematicActorView(slot, bikePrefab, riderPrefab, content.RiderClips, root.transform));
                }
                AddProp(ContentRegistry.Route.Guardrail, new Vector3(8.7f, 0, 4), 0);
                AddProp(ContentRegistry.Route.Chevron, new Vector3(-9.2f, 0, 13), 15);
                foreach (var renderer in stage.GetComponentsInChildren<Renderer>(true))
                { hidden.Add(new RendererState(renderer)); renderer.forceRenderingOff = true; }
                var camera = stage.ViewCamera; cameraPosition = camera.transform.position; cameraRotation = camera.transform.rotation; cameraFov = camera.fieldOfView; cameraCaptured = true;
                Current = definition; IsPlaying = true; ElapsedSeconds = 0; startTime = Time.unscaledTime; beatIndex = -1;
                Evaluate(0); MusicRequested?.Invoke(definition.AudioId); Changed?.Invoke(); return true;
            }
            catch (Exception error)
            {
                LastErrorCode = "scene-open-failed"; LastError = "Không thể mở cảnh phim: " + error.GetType().Name; Cleanup(); Current = null; IsPlaying = false; Changed?.Invoke(); return false;
            }
        }
        private void AddProp(GameObject prefab, Vector3 point, float yaw)
        {
            if (prefab == null) return;
            var item = Instantiate(prefab, root.transform); item.name = "Cinematic prop / " + prefab.name;
            DisablePhysics(item); item.transform.position = WorldPoint(point);
            item.transform.rotation = WorldHeading(point.z) * Quaternion.Euler(0, yaw, 0); props.Add(item);
        }
        private static void DisablePhysics(GameObject item)
        {
            foreach (var collider in item.GetComponentsInChildren<Collider>(true)) collider.enabled = false;
            foreach (var body in item.GetComponentsInChildren<Rigidbody>(true)) { body.isKinematic = true; body.detectCollisions = false; }
            foreach (var child in item.GetComponentsInChildren<Transform>(true)) child.gameObject.isStatic = false;
        }
        public void Evaluate(float seconds)
        {
            if (!IsPlaying || Current == null) return;
            ElapsedSeconds = Mathf.Clamp(float.IsNaN(seconds) || float.IsInfinity(seconds) ? 0 : seconds, 0, Current.DurationSeconds);
            int index = Current.Beats.Count - 1;
            for (int i = 0; i < Current.Beats.Count; i++) if (ElapsedSeconds < Current.Beats[i].EndSeconds) { index = i; break; }
            var beat = Current.Beats[index]; CurrentBeat = beat;
            float phase = Mathf.Clamp(ElapsedSeconds - beat.StartSeconds, 0, beat.DurationSeconds);
            float t = beat.DurationSeconds <= 0 ? 1 : phase / beat.DurationSeconds;
            float eased = t * t * (3 - 2 * t);
            foreach (var pair in actors) pair.Value.SetVisible(false);
            foreach (var cue in beat.Actors)
            {
                if (!actors.TryGetValue(cue.Slot, out var actor)) continue;
                actor.SetVisible(cue.Visible);
                var point = Vector3.Lerp(ToVector(cue.PositionFrom), ToVector(cue.PositionTo), eased);
                var rotation = WorldHeading(point.z) * Quaternion.Euler(0, Mathf.LerpAngle(cue.YawFrom, cue.YawTo, eased), 0);
                actor.Render(WorldPoint(point), rotation, cue.Action, phase, ReducedMotion);
            }
            float cameraT = ReducedMotion ? .5f : eased;
            var position = Vector3.Lerp(ToVector(beat.CameraFrom), ToVector(beat.CameraTo), cameraT);
            var look = Vector3.Lerp(ToVector(beat.LookAtFrom), ToVector(beat.LookAtTo), cameraT);
            var camera = stage.ViewCamera; camera.transform.position = WorldPoint(position);
            Vector3 direction = WorldPoint(look) - camera.transform.position;
            if (direction.sqrMagnitude > .0001f) camera.transform.rotation = Quaternion.LookRotation(direction, Vector3.up);
            camera.fieldOfView = Mathf.Lerp(beat.FieldOfViewFrom, beat.FieldOfViewTo, cameraT);
            if (index != beatIndex) { beatIndex = index; Changed?.Invoke(); }
        }
        private void LateUpdate()
        {
            if (!IsPlaying) return;
            if (stage == null || stage.Road == null || stage.ViewCamera == null || ContentRegistry.Actors == null || ContentRegistry.Route == null) { Stop(true); return; }
            float elapsed = Time.unscaledTime - startTime;
            Evaluate(elapsed);
            if (elapsed >= Current.DurationSeconds) Stop(false);
        }
        public void Stop(bool skipped = true)
        {
            bool active = IsPlaying; var definition = Current;
            IsPlaying = false; Current = null; CurrentBeat = null; ElapsedSeconds = 0; beatIndex = -1;
            Cleanup();
            if (active) { Completed?.Invoke(definition, skipped); Changed?.Invoke(); }
        }
        private void Cleanup()
        {
            foreach (var actor in actors.Values) actor.Dispose(); actors.Clear(); props.Clear();
            if (root != null) { root.SetActive(false); Destroy(root); root = null; }
            foreach (var state in hidden) if (state.Renderer != null) state.Renderer.forceRenderingOff = state.ForceOff;
            hidden.Clear();
            if (cameraCaptured && stage != null && stage.ViewCamera != null)
            { stage.ViewCamera.transform.SetPositionAndRotation(cameraPosition, cameraRotation); stage.ViewCamera.fieldOfView = cameraFov; }
            cameraCaptured = false;
        }
        public CinematicFrameCheck InspectCurrentFrame()
        {
            var check = new CinematicFrameCheck { sequence = Current?.Id ?? "", time = ElapsedSeconds, actorCount = actors.Count, propCount = props.Count };
            if (!IsPlaying || root == null || stage == null || stage.ViewCamera == null) { check.issues.Add("director-not-playing"); return check; }
            var camera = stage.ViewCamera;
            if (!Finite(camera.transform.position) || !Finite(camera.transform.rotation) || !Finite(camera.fieldOfView)) check.issues.Add("camera-nonfinite");
            foreach (var actor in actors.Values)
            {
                if (!actor.SamplingValid) check.issues.Add("clip-time-outside-bounds");
                foreach (var node in actor.Rider.GetComponentsInChildren<Transform>(true)) if (!Finite(node.position) || !Finite(node.rotation) || !Finite(node.lossyScale)) check.issues.Add("actor-nonfinite");
            }
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(false))
            {
                check.renderers++;
                if (renderer.enabled && !renderer.forceRenderingOff && renderer.gameObject.activeInHierarchy) check.enabledRenderers++;
                if (!Finite(renderer.bounds.center) || !Finite(renderer.bounds.size) || renderer.bounds.size.sqrMagnitude < .000001f) check.issues.Add("invalid-renderer-bounds");
                foreach (var material in renderer.sharedMaterials) if (material == null) check.issues.Add("missing-material");
                if (renderer is SkinnedMeshRenderer skin && skin.sharedMesh == null) check.issues.Add("missing-skinned-mesh");
                var mesh = renderer.GetComponent<MeshFilter>(); if (mesh != null && mesh.sharedMesh == null) check.issues.Add("missing-mesh");
            }
            if (check.renderers == 0 || check.enabledRenderers == 0) check.issues.Add("no-enabled-renderers"); check.passed = check.issues.Count == 0; return check;
        }
        private Vector3 WorldPoint(Vector3 point) => stage.Road.transform.TransformPoint(stage.Road.Point(AnchorMeters + point.z, point.x, point.y));
        private Quaternion WorldHeading(float z) => stage.Road.transform.rotation * stage.Road.Heading(AnchorMeters + z);
        private static Vector3 ToVector(CinematicPoint p) => new Vector3(p.X, p.Y, p.Z);
        private static bool Finite(float n) => !float.IsNaN(n) && !float.IsInfinity(n);
        private static bool Finite(Vector3 p) => Finite(p.x) && Finite(p.y) && Finite(p.z);
        private static bool Finite(Quaternion q) => Finite(q.x) && Finite(q.y) && Finite(q.z) && Finite(q.w);
        private void OnDisable() { Stop(true); }
        private void OnDestroy() { Stop(true); Completed = null; MusicRequested = null; Changed = null; }

        private sealed class CinematicActorView : IDisposable
        {
            public readonly GameObject Bike, Rider;
            private readonly CinematicPoseSampler sampler;
            private readonly Transform armRight, armLeft, head;
            private readonly Dictionary<Transform, Quaternion> wheels = new Dictionary<Transform, Quaternion>();
            private readonly Quaternion bikeBasis, bikeBasisInverse;
            public bool SamplingValid => sampler.SamplingValid;
            public CinematicActorView(int slot, GameObject bike, GameObject rider, AnimationClip[] clips, Transform parent)
            {
                if (bike == null || rider == null) throw new InvalidOperationException("Missing cinematic prefab.");
                Bike = Instantiate(bike, parent); Rider = Instantiate(rider, parent); Bike.name = "Cinematic bike " + slot; Rider.name = "Cinematic rider " + slot;
                DisablePhysics(Bike); DisablePhysics(Rider); sampler = new CinematicPoseSampler(Rider.transform, clips);
                var model = Bike.transform.Find("Model"); bikeBasis = model == null ? Quaternion.identity : model.localRotation; bikeBasisInverse = Quaternion.Inverse(bikeBasis);
                foreach (var part in Bike.GetComponentsInChildren<Transform>(true))
                    if (part.name.EndsWith("_Wheel_Front", StringComparison.Ordinal) || part.name.EndsWith("_Wheel_Rear", StringComparison.Ordinal)) wheels[part] = part.localRotation;
                foreach (var bone in Rider.GetComponentsInChildren<Transform>(true))
                { if (bone.name == "UpperArm_R") armRight = bone; else if (bone.name == "UpperArm_L") armLeft = bone; else if (bone.name == "Head") head = bone; }
            }
            public void SetVisible(bool value) { if (Bike != null) Bike.SetActive(value); if (Rider != null) Rider.SetActive(value); }
            public void Render(Vector3 position, Quaternion rotation, string action, float phase, bool reduced)
            {
                bool walking = action == "Run";
                bool standing = walking || action == "Idle" || action == "Converse" || action == "Celebrate" || action == "Inspect" || action == "Busted" || action == "PitWork";
                float lean = action == "LeanLeft" ? -12 : action == "LeanRight" ? 12 : 0;
                Bike.transform.SetPositionAndRotation(position, rotation * Quaternion.Euler(0, 0, lean));
                Vector3 offset = standing ? new Vector3(.8f, 0, 0) : new Vector3(0, -.08f, -.32f);
                Rider.transform.SetPositionAndRotation(position + rotation * offset, rotation * Quaternion.Euler(0, 0, lean * .6f));
                sampler.Sample(action, phase);
                foreach (var wheel in wheels) wheel.Key.localRotation = wheel.Value * bikeBasisInverse * Quaternion.Euler(action == "Ride" ? Mathf.Repeat(phase * 100, 360) : 0, 0, 0) * bikeBasis;
                if (action == "Celebrate")
                { if (armLeft != null) armLeft.localRotation *= Quaternion.Euler(-20, 0, -70); if (armRight != null) armRight.localRotation *= Quaternion.Euler(-20, 0, 70); }
                else if (action == "Converse")
                { if (armRight != null) armRight.localRotation *= Quaternion.Euler(-18, 0, 28 + (reduced ? 0 : Mathf.Sin(phase * 2.8f) * 5)); if (head != null) head.localRotation *= Quaternion.Euler(reduced ? 0 : Mathf.Sin(phase * 2) * 3, 8, 0); }
                else if (action == "Inspect" || action == "PitWork")
                { if (head != null) head.localRotation *= Quaternion.Euler(14, -12, 0); if (armRight != null) armRight.localRotation *= Quaternion.Euler(-35, 0, 12); }
            }
            public void Dispose() { sampler.Dispose(); }
        }
    }

    [Serializable]
    public sealed class CinematicFrameCheck
    {
        public bool passed; public string sequence; public float time; public int actorCount, propCount, renderers, enabledRenderers;
        public List<string> issues = new List<string>();
    }
}
