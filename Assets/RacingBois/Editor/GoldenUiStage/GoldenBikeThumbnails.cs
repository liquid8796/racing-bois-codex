#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Owns real, temporary candidate renders. Never writes sprites or changes source materials.</summary>
    internal sealed class GoldenBikeThumbnails : IDisposable
    {
        private readonly List<Sprite> sprites = new List<Sprite>();
        private readonly List<Texture2D> textures = new List<Texture2D>();

        internal Sprite Render(GameObject prefab, Vector3 rotation)
        {
            var preview = new PreviewRenderUtility();
            var previousTarget = RenderTexture.active;
            Texture2D texture = null;
            try
            {
                var actor = preview.InstantiatePrefabInScene(prefab);
                actor.SetActive(true);
                actor.transform.SetPositionAndRotation(Vector3.zero, Quaternion.Euler(rotation));
                foreach (var collider in actor.GetComponentsInChildren<Collider>(true)) collider.enabled = false;
                foreach (var lod in actor.GetComponentsInChildren<LODGroup>()) lod.ForceLOD(0);
                preview.camera.clearFlags = CameraClearFlags.SolidColor;
                preview.camera.backgroundColor = Color.clear;
                preview.camera.allowHDR = false;
                preview.lights[0].intensity = 1.6f;
                preview.lights[0].transform.rotation = Quaternion.Euler(40, 30, 0);
                preview.lights[1].intensity = 1.1f;
                preview.lights[1].transform.rotation = Quaternion.Euler(30, 160, 0);
                preview.ambientColor = new Color(.3f, .3f, .3f);
                preview.BeginPreview(new Rect(0, 0, 440, 272), GUIStyle.none);
                GoldenUiStageCamera.Frame(preview.camera, GoldenUiStageCamera.Measure(actor),
                    new Vector3(0, .17f, -1), 30, new Rect(.04f, .06f, .92f, .88f));
                // Preserve the measured perspective/projection; PreviewRenderUtility's default resets FOV.
                preview.Render(true, false);
                var rendered = preview.EndPreview() as RenderTexture;
                if (rendered == null) throw new InvalidOperationException("Candidate thumbnail did not render.");
                RenderTexture.active = rendered;
                texture = new Texture2D(rendered.width, rendered.height, TextureFormat.RGBA32, false)
                { name = "Golden thumbnail - " + prefab.name, hideFlags = HideFlags.DontSave };
                texture.ReadPixels(new Rect(0, 0, rendered.width, rendered.height), 0, 0);
                texture.Apply();
                var sprite = Sprite.Create(texture, new Rect(0, 0, texture.width, texture.height), new Vector2(.5f, .5f));
                sprite.name = texture.name; sprite.hideFlags = HideFlags.DontSave;
                textures.Add(texture); sprites.Add(sprite); texture = null;
                return sprite;
            }
            finally
            {
                RenderTexture.active = previousTarget;
                if (texture != null) UnityEngine.Object.DestroyImmediate(texture);
                preview.Cleanup();
            }
        }

        public void Dispose()
        {
            foreach (var sprite in sprites) if (sprite != null) UnityEngine.Object.DestroyImmediate(sprite);
            foreach (var texture in textures) if (texture != null) UnityEngine.Object.DestroyImmediate(texture);
            sprites.Clear(); textures.Clear();
        }
    }
}
#endif
