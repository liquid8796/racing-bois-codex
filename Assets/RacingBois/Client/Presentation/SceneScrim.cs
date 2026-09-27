using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    /// <summary>Local contrast behind menu copy and navigation over a changing 3D scene.</summary>
    internal sealed class SceneScrim : VisualElement
    {
        private static readonly float[] Stops = { 0f, .28f, .48f, .78f, 1f };
        private static readonly byte[] Opacity = { 210, 190, 94, 0, 0 };
        private static readonly float[] TopStops = { 0f, .05f, .10f, .16f, .22f };
        private static readonly byte[] TopOpacity = { 218, 206, 166, 48, 0 };

        public SceneScrim()
        {
            name = "scene-scrim";
            pickingMode = PickingMode.Ignore;
            style.position = Position.Absolute;
            style.left = style.right = style.top = style.bottom = 0;
            generateVisualContent += Draw;
        }

        private void Draw(MeshGenerationContext context)
        {
            if (contentRect.width <= 0 || contentRect.height <= 0) return;
            var mesh = context.Allocate(Stops.Length * 2, (Stops.Length - 1) * 6);
            for (int i = 0; i < Stops.Length; i++)
            {
                float x = Stops[i] * contentRect.width;
                var tint = new Color32(10, 12, 13, Opacity[i]);
                mesh.SetNextVertex(new Vertex { position = new Vector3(x, 0, Vertex.nearZ), tint = tint });
                mesh.SetNextVertex(new Vertex { position = new Vector3(x, contentRect.height, Vertex.nearZ), tint = tint });
            }
            for (ushort i = 0; i < Stops.Length - 1; i++)
            {
                ushort a = (ushort)(i * 2);
                mesh.SetNextIndex(a); mesh.SetNextIndex((ushort)(a + 2)); mesh.SetNextIndex((ushort)(a + 1));
                mesh.SetNextIndex((ushort)(a + 1)); mesh.SetNextIndex((ushort)(a + 2)); mesh.SetNextIndex((ushort)(a + 3));
            }
            // A shallow fade protects the top navigation against a bright horizon;
            // it does not cover the hero or introduce a panel behind every control.
            var top = context.Allocate(TopStops.Length * 2, (TopStops.Length - 1) * 6);
            for (int i = 0; i < TopStops.Length; i++)
            {
                float y = TopStops[i] * contentRect.height;
                var tint = new Color32(10, 12, 13, TopOpacity[i]);
                top.SetNextVertex(new Vertex { position = new Vector3(0, y, Vertex.nearZ), tint = tint });
                top.SetNextVertex(new Vertex { position = new Vector3(contentRect.width, y, Vertex.nearZ), tint = tint });
            }
            for (ushort i = 0; i < TopStops.Length - 1; i++)
            {
                ushort a = (ushort)(i * 2);
                top.SetNextIndex(a); top.SetNextIndex((ushort)(a + 1)); top.SetNextIndex((ushort)(a + 2));
                top.SetNextIndex((ushort)(a + 2)); top.SetNextIndex((ushort)(a + 1)); top.SetNextIndex((ushort)(a + 3));
            }
        }
    }
}
