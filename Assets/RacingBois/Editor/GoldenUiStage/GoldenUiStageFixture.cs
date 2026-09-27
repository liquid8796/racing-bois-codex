#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using RacingBois.Client.Application;
using RacingBois.Client.Bootstrap;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using RacingBois.Golden;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace RacingBois.Authoring.Editor
{
    /// <summary>
    /// Reversible, editor-only visual staging of real candidate prefabs over the actual UI.
    /// Never edits ProductionContent, ContentRegistry, credentials, accounts, assets or scene files.
    /// </summary>
    public static class GoldenUiStageFixture
    {
        private static Session active;
        public static bool IsOpen => active != null;
        public static string OpenMain(RaceBootstrap context = null, GoldenUiStageConfiguration configuration = null)
        {
            if (IsOpen) throw new InvalidOperationException("Close the current golden UI stage first.");
            context = context != null ? context : FindContext();
            Validate(context);
            var candidate = new Session(context, configuration ?? new GoldenUiStageConfiguration());
            try
            {
                candidate.Open(); active = candidate;
                EditorApplication.update += Tick;
                EditorApplication.playModeStateChanged += PlayModeChanged;
                AssemblyReloadEvents.beforeAssemblyReload += Close;
                EditorApplication.quitting += Close;
                return Describe();
            }
            catch { candidate.Dispose(); throw; }
        }
        public static string OpenGarage(RaceBootstrap context = null, GoldenUiStageConfiguration configuration = null)
        {
            try { if (!IsOpen) OpenMain(context, configuration); active.ShowGarage(); return Describe(); }
            catch { Close(); throw; }
        }
        public static string ShowMain()
        { try { NeedSession().ShowMain(); return Describe(); } catch { Close(); throw; } }
        public static string Describe() => active == null ? "Golden UI fixture closed." : JsonUtility.ToJson(active.Report(), true);
        public static void SetControlsVisible(bool visible) => NeedSession().SetControlsVisible(visible);
        public static void Close()
        {
            EditorApplication.update -= Tick;
            EditorApplication.playModeStateChanged -= PlayModeChanged;
            AssemblyReloadEvents.beforeAssemblyReload -= Close;
            EditorApplication.quitting -= Close;
            var previous = active; active = null; previous?.Dispose();
        }
        private static Session NeedSession() => active ?? throw new InvalidOperationException("Open the golden UI fixture first.");
        private static void Tick()
        {
            if (active == null) return;
            try { if (!active.IsContextIdle) Close(); else active.Tick(); }
            catch (Exception error) { Close(); Debug.LogException(error); }
        }
        private static void PlayModeChanged(PlayModeStateChange state)
        { if (state == PlayModeStateChange.ExitingPlayMode || state == PlayModeStateChange.EnteredEditMode) Close(); }
        private static RaceBootstrap FindContext()
        {
            var contexts = UnityEngine.Object.FindObjectsByType<RaceBootstrap>(FindObjectsInactive.Exclude);
            if (contexts.Length != 1) throw new InvalidOperationException("Pass the exact live RaceBootstrap; scene context is missing or ambiguous.");
            return contexts[0];
        }
        private static bool Disconnected(SessionStatus status) => status == SessionStatus.Offline || status == SessionStatus.Failed;
        private static void Validate(RaceBootstrap context)
        {
            if (!EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("The fixture requires idle Play mode.");
            if (context == null || context.Stage == null || context.Stage.Road == null || context.Stage.ViewCamera == null || context.Document == null)
                throw new InvalidOperationException("The supplied RaceBootstrap does not have its actual stage, road, camera and UI references.");
            if (context.Session == null || context.Multiplayer == null || !Disconnected(context.Session.Status) || !Disconnected(context.Multiplayer.Status) || context.Multiplayer.Room != null)
                throw new InvalidOperationException("Leave the race/room and disconnect before visual staging.");
            var screen = context.GetComponent<RaceScreen>();
            if (screen == null || !screen.IsMenuOpen || screen.SettingsOpen || screen.PracticeOpen || screen.ContentBusy || context.ContentLoader == null || context.ContentLoader.Busy)
                throw new InvalidOperationException("Use the idle main menu, with content/settings/practice overlays closed.");
            if (GaragePrototypeFixture.IsOpen || context.GetComponents<CareerView>().Any(view => view.IsOpen))
                throw new InvalidOperationException("Close an existing career/garage fixture first.");
            var cinematics = context.GetComponent<BootstrapCinematicCoordinator>();
            if (cinematics != null && cinematics.BlocksGameplayInput) throw new InvalidOperationException("Close the gallery or cutscene before staging.");
            if (context.Document.rootVisualElement.Q("surface") == null) throw new InvalidOperationException("The current UIDocument has no initialized surface.");
            if (context.transform.IsChildOf(context.Stage.transform) || context.transform.IsChildOf(context.Stage.Road.transform) ||
                context.Document.transform.IsChildOf(context.Stage.transform) || context.Document.transform.IsChildOf(context.Stage.Road.transform))
                throw new InvalidOperationException("The supplied presentation subtree also owns the app/UI; it cannot be hidden independently.");
            foreach (var camera in Camera.allCameras)
                if (camera != context.Stage.ViewCamera && camera.cameraType == CameraType.Game && camera.enabled && camera.targetTexture == null && camera.targetDisplay == context.Stage.ViewCamera.targetDisplay)
                    throw new InvalidOperationException("An unrelated Game camera also renders this display. Resolve it explicitly before opening the fixture.");
        }

        [Serializable] private sealed class CaptureReport
        {
            public string mode, apexPrefab, ashPrefab, riderPreviewClip, environmentPrefab, workshopPrefab, workshopScene, workshopState, workshopError, workshopSceneSha256, mainConceptSha256, garageConceptSha256, knownFailures;
            public bool workshopReady;
            public int workshopLightmappedRenderers, workshopReflections, workshopProbePositions;
            public bool visualAccepted, workshopMissing, selectedBikeMissing, renderedThumbnailsMissing, aspectMatchesReference;
            public float actualAspect, verticalFov;
            public Vector3 cameraPosition, cameraEuler, subjectCenter, subjectSize;
            public Rect targetRect, projectedBounds;
        }

        private sealed class Session : IDisposable
        {
            private readonly RaceBootstrap context;
            private readonly GoldenUiStageConfiguration settings;
            private readonly List<Action> restore = new List<Action>();
            private readonly HashSet<GameObject> capturedObjects = new HashSet<GameObject>();
            private GameObject owner, apex, ash, environment, workshop;
            private GoldenUiWorkshopScope bakedWorkshop;
            private GoldenUiStageFocus previewFocus;
            private Camera camera;
            private VisualElement toolbar, controlRow, garageRoot, previousFocus;
            private Label notice;
            private GoldenUiStageInputScope input;
            private bool garageMode, ownsGarage, selectedBikeMissing, disposed;
            private int apexIndex;
            private float lastAspect;
            private Bounds subjectBounds;
            private GoldenUiStageCamera.Geometry subjectGeometry;
            private Rect targetRect, projectedBounds;
            internal Session(RaceBootstrap context, GoldenUiStageConfiguration settings) { this.context = context; this.settings = settings; }
            internal bool IsContextIdle => context != null && context.Stage != null && context.Document != null &&
                context.gameObject.scene.IsValid() && context.gameObject.scene.isLoaded && EditorApplication.isPlaying &&
                context.Session != null && context.Multiplayer != null && Disconnected(context.Session.Status) &&
                Disconnected(context.Multiplayer.Status) && context.Multiplayer.Room == null && context.ContentLoader != null && !context.ContentLoader.Busy;

            internal void Open()
            {
                // Validate inputs before touching the live presentation.
                var apexAsset = Prefab(settings.ApexPrefab); var ashAsset = Prefab(settings.AshPrefab); var environmentAsset = Prefab(settings.EnvironmentPrefab);
                var workshopAsset = string.IsNullOrWhiteSpace(settings.WorkshopPrefab) ? null : Prefab(settings.WorkshopPrefab);
                if (workshopAsset != null && !string.IsNullOrEmpty(settings.WorkshopScenePath)) throw new InvalidOperationException("Select a baked workshop scene or an unbaked prefab, not both.");
                apexIndex = BikeCatalog.All.Single(value => value.Id == "rb-apex").CatalogIndex;
                previousFocus = context.Document.rootVisualElement.panel?.focusController.focusedElement as VisualElement;
                bool bootstrapEnabled = context.enabled; restore.Add(() => { if (context != null) context.enabled = bootstrapEnabled; }); context.enabled = false;
                Hide(context.Stage.gameObject); Hide(context.Stage.Road.gameObject);
                var originalCamera = context.Stage.ViewCamera; bool cameraEnabled = originalCamera.enabled;
                restore.Add(() => { if (originalCamera != null) originalCamera.enabled = cameraEnabled; }); originalCamera.enabled = false;
                owner = new GameObject("Golden UI stage - unaccepted editor candidates") { hideFlags = HideFlags.DontSave };
                owner.SetActive(false);
                SceneManager.MoveGameObjectToScene(owner, context.gameObject.scene);
                var lighting = new GoldenUiStageLighting(owner, settings);
                restore.Add(lighting.Dispose);
                apex = Spawn(apexAsset); ash = Spawn(ashAsset); environment = Spawn(environmentAsset);
                if (workshopAsset != null) workshop = Spawn(workshopAsset);
                apex.transform.SetPositionAndRotation(settings.BikePosition, Quaternion.Euler(settings.BikeEuler));
                ash.transform.SetPositionAndRotation(settings.StandingRiderPosition, Quaternion.Euler(settings.StandingRiderEuler));
                environment.transform.SetPositionAndRotation(settings.EnvironmentPosition, Quaternion.Euler(settings.EnvironmentEuler));
                var animator = ash.GetComponentInChildren<Animator>(true);
                var clips = RiderAnimationSet.Resolve(ash.transform, null);
                if (animator == null || clips == null) throw new InvalidOperationException("Ash candidate has no real authored animation override.");
                var preview = ResolvePreviewClip(clips);
                animator.enabled = false; animator.applyRootMotion = false; preview.SampleAnimation(animator.gameObject, 0);
                var cameraOwner = new GameObject("Golden UI candidate camera") { hideFlags = HideFlags.DontSave }; cameraOwner.transform.SetParent(owner.transform, false);
                camera = cameraOwner.AddComponent<Camera>(); camera.CopyFrom(originalCamera); camera.targetTexture = null; camera.enabled = true;
                var sourceData = originalCamera.GetComponent<UniversalAdditionalCameraData>();
                var data = camera.GetUniversalAdditionalCameraData();
                data.renderPostProcessing = true;
                if (sourceData != null) data.antialiasing = sourceData.antialiasing;
                if (!string.IsNullOrEmpty(settings.WorkshopScenePath))
                {
                    var fixtureLighting = owner.GetComponentsInChildren<Behaviour>(true).Where(value => value is Light || value is ReflectionProbe || value is UnityEngine.Rendering.Volume).ToArray();
                    bakedWorkshop = new GoldenUiWorkshopScope(settings.WorkshopScenePath, settings.WorkshopRoomIdentity, owner, fixtureLighting);
                    bakedWorkshop.Changed += UpdateNotice;
                }
                previewFocus = new GoldenUiStageFocus(owner, camera);
                SetLabel("title", "CANYON RUN"); SetLabel("menu-level", "CẤP 1 /"); SetLabel("menu-selection", "APEX");
                BuildToolbar();
                input = new GoldenUiStageInputScope(context.Document.rootVisualElement, toolbar, () => garageRoot, Close);
                owner.SetActive(true);
                ShowMain();
            }
            private static GameObject Prefab(string path)
            {
                var value = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (value == null || !PrefabUtility.IsPartOfPrefabAsset(value)) throw new InvalidOperationException("Missing imported candidate prefab: " + path);
                foreach (var behavior in value.GetComponentsInChildren<MonoBehaviour>(true))
                    if (behavior == null || !(behavior is RiderAnimationSet) && !(behavior is GoldenSkinBounds))
                        throw new InvalidOperationException("Candidate prefab has a missing or unaudited behavior: " + path);
                return value;
            }
            private AnimationClip ResolvePreviewClip(AnimationClip[] gameplayClips)
            {
                if (string.IsNullOrEmpty(settings.MainRiderClipSource) && string.IsNullOrEmpty(settings.MainRiderClipName))
                    return gameplayClips.Single(clip => clip != null && clip.name.EndsWith("RB_Idle", StringComparison.Ordinal));
                if (string.IsNullOrEmpty(settings.MainRiderClipSource) || string.IsNullOrEmpty(settings.MainRiderClipName))
                    throw new InvalidOperationException("The preview pose requires both its source asset and exact clip name.");
                var matches = AssetDatabase.LoadAllAssetsAtPath(settings.MainRiderClipSource).OfType<AnimationClip>()
                    .Where(clip => clip.name == settings.MainRiderClipName && clip.length > 0).ToArray();
                if (matches.Length != 1) throw new InvalidOperationException("Missing or ambiguous authored menu pose: " + settings.MainRiderClipName);
                return matches[0];
            }
            private GameObject Spawn(GameObject prefab)
            {
                var instance = UnityEngine.Object.Instantiate(prefab, owner.transform, false); instance.hideFlags = HideFlags.DontSave;
                foreach (var collider in instance.GetComponentsInChildren<Collider>(true)) collider.enabled = false;
                foreach (var body in instance.GetComponentsInChildren<Rigidbody>(true)) { body.isKinematic = true; body.detectCollisions = false; }
                return instance;
            }
            private void Hide(GameObject value)
            {
                if (!capturedObjects.Add(value)) return;
                bool state = value.activeSelf; restore.Add(() => { if (value != null) value.SetActive(state); }); value.SetActive(false);
            }
            private void SetLabel(string name, string text)
            {
                var label = context.Document.rootVisualElement.Q<Label>(name);
                if (label == null) throw new InvalidOperationException("Missing actual menu binding: " + name);
                string original = label.text; restore.Add(() => label.text = original); label.text = text;
            }
            private void BuildToolbar()
            {
                toolbar = new VisualElement { name = "golden-ui-fixture-notice" };
                toolbar.style.position = Position.Absolute; toolbar.style.left = 20; toolbar.style.top = 90;
                toolbar.style.backgroundColor = new Color(.025f, .035f, .045f, .95f); toolbar.style.paddingLeft = toolbar.style.paddingRight = 9;
                var row = new VisualElement(); controlRow = row; row.style.flexDirection = FlexDirection.Row;
                row.Add(new Button(() => GoldenUiStageFixture.ShowMain()) { text = "FIXTURE: MENU" }); row.Add(new Button(() => OpenGarage()) { text = "FIXTURE: GARAGE" }); row.Add(new Button(Close) { text = "ĐÓNG FIXTURE" });
                toolbar.Add(row); notice = new Label(); notice.style.fontSize = 12; notice.style.color = new Color(1, .76f, .34f); toolbar.Add(notice);
                context.Document.rootVisualElement.Add(toolbar);
            }
            internal void SetControlsVisible(bool visible)
            { controlRow.style.display = visible ? DisplayStyle.Flex : DisplayStyle.None; }
            internal void ShowMain()
            {
                if (ownsGarage) { ownsGarage = false; GaragePrototypeFixture.Close(); }
                garageRoot = null; garageMode = false; selectedBikeMissing = false;
                bakedWorkshop?.SetGarageVisible(false);
                apex.transform.SetPositionAndRotation(settings.BikePosition, Quaternion.Euler(settings.BikeEuler));
                apex.SetActive(true); ash.SetActive(true); environment.SetActive(true); if (workshop != null) workshop.SetActive(false);
                ForceVisibleLods();
                camera.clearFlags = string.IsNullOrEmpty(settings.MainSkyMaterial) ? context.Stage.ViewCamera.clearFlags : CameraClearFlags.Skybox;
                camera.backgroundColor = context.Stage.ViewCamera.backgroundColor;
                subjectGeometry = GoldenUiStageCamera.Measure(apex, ash); subjectBounds = subjectGeometry.Bounds; targetRect = settings.MainSubjectRect; Reframe(); UpdateNotice();
            }
            internal void ShowGarage()
            {
                if (garageMode) return;
                var surface = context.Document.rootVisualElement.Q("surface"); var previousChildren = new HashSet<VisualElement>(surface.Children());
                GaragePrototypeFixture.Open(context.Document, settings.RenderedBikeThumbnails, PreviewBike); ownsGarage = true;
                garageRoot = surface.Children().Single(child => !previousChildren.Contains(child) && child.name == "career");
                garageMode = true; selectedBikeMissing = false; apex.SetActive(true); ash.SetActive(false); environment.SetActive(false); if (workshop != null) workshop.SetActive(true);
                ForceVisibleLods();
                apex.transform.SetPositionAndRotation(settings.BikePosition, Quaternion.Euler(settings.GarageBikeEuler));
                bakedWorkshop?.SetGarageVisible(true);
                camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.025f, .025f, .028f);
                subjectGeometry = GoldenUiStageCamera.Measure(apex); subjectBounds = subjectGeometry.Bounds; targetRect = settings.GarageSubjectRect; Reframe(); UpdateNotice();
            }
            private void PreviewBike(int index)
            {
                selectedBikeMissing = index != apexIndex; if (apex != null) apex.SetActive(!selectedBikeMissing); UpdateNotice();
            }
            private void ForceVisibleLods()
            {
                foreach (var lod in owner.GetComponentsInChildren<LODGroup>())
                    if (lod.enabled && lod.gameObject.activeInHierarchy) lod.ForceLOD(0);
            }
            internal void Tick()
            {
                if (garageMode && ownsGarage && !GaragePrototypeFixture.IsOpen) { ownsGarage = false; ShowMain(); }
                if (camera != null && !Mathf.Approximately(lastAspect, camera.aspect)) Reframe();
            }
            private void Reframe()
            {
                projectedBounds = GoldenUiStageCamera.Frame(camera, subjectGeometry, garageMode ? settings.GarageCameraDirection : settings.CameraDirection, garageMode ? settings.GarageVerticalFov : settings.MainVerticalFov, targetRect);
                previewFocus?.Apply(garageMode && settings.GarageDepthOfField, Vector3.Distance(camera.transform.position, subjectBounds.center));
                lastAspect = camera.aspect;
            }
            private void UpdateNotice()
            {
                if (notice == null) return;
                notice.text = "EDITOR FIXTURE · MODEL CHƯA NGHIỆM THU · KHÔNG GHI HỒ SƠ" +
                    (garageMode && workshop == null && bakedWorkshop == null ? " · THIẾU XƯỞNG 3D" : "") +
                    (garageMode && bakedWorkshop != null && !bakedWorkshop.IsReady ? " · XƯỞNG: " + bakedWorkshop.State : "") +
                    (selectedBikeMissing ? " · XE ĐANG CHỌN CHƯA CÓ CANDIDATE" : "");
                toolbar.BringToFront();
            }
            internal CaptureReport Report() => new CaptureReport
            {
                mode = garageMode ? "garage-v2" : "main-v2", visualAccepted = false,
                apexPrefab = settings.ApexPrefab, ashPrefab = settings.AshPrefab, riderPreviewClip = settings.MainRiderClipName, environmentPrefab = settings.EnvironmentPrefab, workshopPrefab = settings.WorkshopPrefab,
                workshopScene = settings.WorkshopScenePath, workshopState = bakedWorkshop?.State, workshopError = bakedWorkshop?.ErrorCode, workshopReady = bakedWorkshop != null && bakedWorkshop.IsReady,
                workshopSceneSha256 = bakedWorkshop?.LoadedSceneSha256, workshopLightmappedRenderers = bakedWorkshop?.BakedRendererCount ?? 0,
                workshopReflections = bakedWorkshop?.BakedReflectionCount ?? 0, workshopProbePositions = bakedWorkshop?.AuthoredProbePositions ?? 0,
                mainConceptSha256 = GoldenUiStageConfiguration.MainConceptSha256, garageConceptSha256 = GoldenUiStageConfiguration.GarageConceptSha256,
                workshopMissing = workshop == null && bakedWorkshop == null, selectedBikeMissing = selectedBikeMissing, renderedThumbnailsMissing = MissingThumbnails(), actualAspect = camera.aspect,
                aspectMatchesReference = Mathf.Abs(camera.aspect - GoldenUiStageConfiguration.ReferenceAspect) < .01f,
                verticalFov = camera.fieldOfView, cameraPosition = camera.transform.position, cameraEuler = camera.transform.eulerAngles,
                subjectCenter = subjectBounds.center, subjectSize = subjectBounds.size, targetRect = targetRect, projectedBounds = projectedBounds,
                knownFailures = "Candidates are visually unaccepted; the authored menu pose still requires contact checks against the selected bike. " +
                    "A missing real workshop or supplied rendered thumbnail remains a visual failure. Original practice choices, authority and persistence are untouched; menu launch/network intents are blocked in this fixture."
            };
            private bool MissingThumbnails()
            {
                foreach (var identity in new[] { "rb-spark-450", "rb-apex" })
                {
                    int index = BikeCatalog.All.Single(value => value.Id == identity).CatalogIndex;
                    if (settings.RenderedBikeThumbnails == null || index >= settings.RenderedBikeThumbnails.Length || settings.RenderedBikeThumbnails[index] == null) return true;
                }
                return false;
            }
            public void Dispose()
            {
                if (disposed) return; disposed = true;
                if (bakedWorkshop != null) { bakedWorkshop.Changed -= UpdateNotice; Cleanup(bakedWorkshop.Dispose); bakedWorkshop = null; }
                Cleanup(() => previewFocus?.Dispose()); previewFocus = null;
                Cleanup(() => input?.Dispose()); input = null;
                if (ownsGarage) { ownsGarage = false; Cleanup(GaragePrototypeFixture.Close); }
                garageRoot = null; Cleanup(() => toolbar?.RemoveFromHierarchy()); toolbar = null;
                if (owner != null) Cleanup(() => UnityEngine.Object.DestroyImmediate(owner));
                for (int i = restore.Count - 1; i >= 0; i--)
                    Cleanup(restore[i]);
                restore.Clear();
                if (previousFocus != null && previousFocus.panel != null && previousFocus.enabledInHierarchy) previousFocus.Focus();
            }
            private static void Cleanup(Action action)
            { try { action(); } catch (Exception error) { Debug.LogError("Golden UI fixture restoration failed: " + error); } }
        }
    }
}
#endif
