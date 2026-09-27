using System;
using UnityEngine;
using UnityEngine.InputSystem;

namespace RacingBois.Golden
{
    /// <summary>Isolated art inspection controls. Does not reference gameplay, accounts or production content.</summary>
    public sealed class GoldenReviewController : MonoBehaviour
    {
        [Serializable]
        public sealed class Subject
        {
            public string Id;
            public GameObject Root;
            public Vector3 Center;
            public Vector3 Size;
            public bool IsEnvironment;
            public Vector3 GameplayPosition, GameplayTarget;
            public float GameplayVerticalFov = 58f;
        }

        public Camera ReviewCamera;
        public Subject[] Subjects = Array.Empty<Subject>();
        public bool ShowControls = true;
        public float TurntableDegreesPerSecond = 14f;
        public int SubjectIndex { get; private set; }
        public int ViewIndex { get; private set; }
        public int ForcedLod { get; private set; } = -1;
        public bool IsTurning { get; private set; }

        private static readonly string[] Views = { "Three-quarter", "Front (+Z)", "Side (+X)", "Rear (-Z)", "Gameplay", "Detail" };
        private Quaternion[] initialRotations;
        private float turntableAngle;
        private GUIStyle titleStyle, hintStyle;
        private Texture2D panelTexture;
        private float lastAspect;

        private void Awake()
        {
            initialRotations = new Quaternion[Subjects.Length];
            for (int i = 0; i < Subjects.Length; i++)
                initialRotations[i] = Subjects[i].Root == null ? Quaternion.identity : Subjects[i].Root.transform.localRotation;
            SetSubject(0);
        }

        private void Update()
        {
            if (ReviewCamera != null && !Mathf.Approximately(lastAspect, ReviewCamera.aspect)) ApplyCamera();
            var keyboard = Keyboard.current;
            if (keyboard != null)
            {
                if (keyboard.tabKey.wasPressedThisFrame) SetSubject((SubjectIndex + 1) % Math.Max(1, Subjects.Length));
                if (keyboard.digit1Key.wasPressedThisFrame) SetView(0);
                if (keyboard.digit2Key.wasPressedThisFrame) SetView(1);
                if (keyboard.digit3Key.wasPressedThisFrame) SetView(2);
                if (keyboard.digit4Key.wasPressedThisFrame) SetView(3);
                if (keyboard.digit5Key.wasPressedThisFrame) SetView(4);
                if (keyboard.digit6Key.wasPressedThisFrame) SetView(5);
                if (keyboard.spaceKey.wasPressedThisFrame) SetTurntable(!IsTurning);
                if (keyboard.hKey.wasPressedThisFrame) ShowControls = !ShowControls;
                if (keyboard.lKey.wasPressedThisFrame) SetLod(ForcedLod == 2 ? -1 : ForcedLod + 1);
            }
            if (!IsTurning || Subjects.Length == 0 || Subjects[SubjectIndex].Root == null) return;
            turntableAngle = Mathf.Repeat(turntableAngle + Time.unscaledDeltaTime * TurntableDegreesPerSecond, 360f);
            Subjects[SubjectIndex].Root.transform.localRotation = Quaternion.Euler(0, turntableAngle, 0) * initialRotations[SubjectIndex];
        }

        public void SetSubject(int index)
        {
            if (Subjects.Length == 0) return;
            SubjectIndex = Mathf.Clamp(index, 0, Subjects.Length - 1);
            ViewIndex = Subjects[SubjectIndex].IsEnvironment ? 4 : 0;
            ResetRotation();
            for (int i = 0; i < Subjects.Length; i++)
                if (Subjects[i].Root != null) Subjects[i].Root.SetActive(i == SubjectIndex);
            SetLod(ForcedLod);
            ApplyCamera();
        }

        public void SetView(int index)
        {
            ViewIndex = Mathf.Clamp(index, 0, Views.Length - 1);
            IsTurning = false;
            ResetRotation();
            ApplyCamera();
        }

        public void SetTurntable(bool enabled)
        {
            IsTurning = enabled && Subjects.Length > 0 && !Subjects[SubjectIndex].IsEnvironment;
            if (!enabled) ResetRotation();
        }

        public void SetLod(int level)
        {
            ForcedLod = Mathf.Clamp(level, -1, 2);
            foreach (var subject in Subjects)
                if (subject.Root != null)
                    foreach (var lod in subject.Root.GetComponentsInChildren<LODGroup>(true)) lod.ForceLOD(ForcedLod);
        }

        private void ResetRotation()
        {
            turntableAngle = 0;
            if (initialRotations == null) return;
            for (int i = 0; i < Subjects.Length; i++)
                if (Subjects[i].Root != null) Subjects[i].Root.transform.localRotation = initialRotations[i];
        }

        private void ApplyCamera()
        {
            if (ReviewCamera == null || Subjects.Length == 0 || Subjects[SubjectIndex].Root == null) return;
            var subject = Subjects[SubjectIndex];
            if (subject.IsEnvironment && ViewIndex == 4)
            {
                lastAspect = ReviewCamera.aspect;
                ReviewCamera.fieldOfView = subject.GameplayVerticalFov;
                ReviewCamera.nearClipPlane = .05f; ReviewCamera.farClipPlane = 2000;
                ReviewCamera.transform.position = subject.Root.transform.TransformPoint(subject.GameplayPosition);
                ReviewCamera.transform.LookAt(subject.Root.transform.TransformPoint(subject.GameplayTarget), Vector3.up);
                return;
            }
            Vector3 center = subject.Root.transform.TransformPoint(subject.Center);
            float radius = Mathf.Max(.4f, subject.Size.magnitude * .5f);
            lastAspect = ReviewCamera.aspect;
            float verticalFov = ViewIndex == 4 ? 58f : 38f;
            float halfFov = verticalFov * Mathf.Deg2Rad * .5f;
            // Frame against the narrower camera axis; changing window aspect must not crop the specimen.
            float halfHorizontal = Mathf.Atan(Mathf.Tan(halfFov) * Mathf.Max(.25f, ReviewCamera.aspect));
            float distance = radius / Mathf.Sin(Mathf.Min(halfFov, halfHorizontal)) * 1.12f;
            Vector3 direction;
            switch (ViewIndex)
            {
                case 1: direction = new Vector3(0, .12f, 1); break;
                case 2: direction = new Vector3(1, .08f, 0); break;
                case 3: direction = new Vector3(0, .12f, -1); break;
                case 4: direction = new Vector3(0, .27f, -1); distance = Mathf.Max(5.2f, radius * 3.9f); break;
                case 5: direction = new Vector3(.7f, .22f, 1); distance *= .62f; center.y += subject.Size.y * .08f; break;
                default: direction = new Vector3(1, .42f, 1.25f); break;
            }
            ReviewCamera.fieldOfView = verticalFov;
            ReviewCamera.nearClipPlane = .05f;
            ReviewCamera.farClipPlane = Mathf.Max(80, distance * 5);
            ReviewCamera.transform.position = center + direction.normalized * distance;
            ReviewCamera.transform.LookAt(center, Vector3.up);
        }

        private void OnGUI()
        {
            if (!ShowControls || Subjects.Length == 0) return;
            if (titleStyle == null)
            {
                titleStyle = new GUIStyle(GUI.skin.label) { fontSize = 18, fontStyle = FontStyle.Bold };
                hintStyle = new GUIStyle(GUI.skin.label) { fontSize = 12, wordWrap = true };
                panelTexture = new Texture2D(1, 1, TextureFormat.RGBA32, false);
                panelTexture.SetPixel(0, 0, new Color(.035f, .045f, .055f, .92f)); panelTexture.Apply();
            }
            const float width = 364;
            GUI.DrawTexture(new Rect(18, 18, width, 184), panelTexture);
            GUILayout.BeginArea(new Rect(32, 28, width - 28, 166));
            GUILayout.Label("RACING BOIS / ART REVIEW", titleStyle);
            GUILayout.Label(Subjects[SubjectIndex].Id + "  |  " + Views[ViewIndex] + "  |  " + (ForcedLod < 0 ? "Automatic LOD" : "LOD " + ForcedLod), hintStyle);
            GUILayout.Label("Tab: subject   1–6: view   Space: turntable   L: LOD   H: hide controls", hintStyle);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Previous")) SetSubject((SubjectIndex + Subjects.Length - 1) % Subjects.Length);
            if (GUILayout.Button("Next")) SetSubject((SubjectIndex + 1) % Subjects.Length);
            if (GUILayout.Button(IsTurning ? "Stop" : "Turntable")) SetTurntable(!IsTurning);
            GUILayout.EndHorizontal();
            GUILayout.Label("Inspection scene • Visual approval and gameplay integration are separate gates.", hintStyle);
            GUILayout.EndArea();
        }

        private void OnDestroy()
        {
            if (panelTexture != null) Destroy(panelTexture);
        }
    }
}
