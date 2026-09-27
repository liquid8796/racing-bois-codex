using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    /// <summary>Native display adapter. Lists actual monitor resolutions; no display API runs in Web or Editor.</summary>
    internal sealed class DesktopDisplaySettings : IDisposable
    {
        private readonly UiBindingScope bindings = new UiBindingScope();
        private VisualElement owned = null;
#if UNITY_STANDALONE_WIN && !UNITY_EDITOR
        private readonly List<Vector2Int> sizes = new List<Vector2Int>();
        private readonly FullScreenMode[] modes = { FullScreenMode.Windowed, FullScreenMode.FullScreenWindow, FullScreenMode.ExclusiveFullScreen };
        private DropdownField mode, resolution;
        private Label status;
        public void Initialize(VisualElement settings)
        {
            owned = new VisualElement(); owned.AddToClassList("desktop-display-settings");
            var title = new Label("MÀN HÌNH WINDOWS"); title.AddToClassList("eyebrow amber"); owned.Add(title);
            mode = new DropdownField("CHẾ ĐỘ", new List<string> { "Cửa sổ", "Toàn màn hình không viền", "Toàn màn hình độc quyền" }, 0);
            mode.AddToClassList("content-choice"); owned.Add(mode);
            var labels = new List<string>();
            AddSize(Screen.width, Screen.height, labels);
            foreach (var available in Screen.resolutions) AddSize(available.width, available.height, labels);
            resolution = new DropdownField("ĐỘ PHÂN GIẢI", labels, 0); resolution.AddToClassList("content-choice"); owned.Add(resolution);
            int index = Array.IndexOf(modes, Screen.fullScreenMode); mode.index = Math.Max(0, index);
            var apply = new Button { text = "ÁP DỤNG MÀN HÌNH" }; apply.AddToClassList("secondary"); owned.Add(apply); bindings.Click(apply, Apply);
            status = new Label("Độ phân giải lấy từ màn hình hiện tại. Chất lượng hình ảnh được chọn riêng."); status.AddToClassList("hint"); owned.Add(status);
            settings.Q<ScrollView>()?.Add(owned);
        }
        private void AddSize(int width, int height, List<string> labels)
        {
            var value = new Vector2Int(width, height);
            if (width <= 0 || height <= 0 || sizes.Contains(value)) return;
            sizes.Add(value); labels.Add(width + " × " + height);
        }
        private void Apply()
        {
            if (resolution.index < 0 || resolution.index >= sizes.Count || mode.index < 0 || mode.index >= modes.Length) return;
            var size = sizes[resolution.index]; Screen.SetResolution(size.x, size.y, modes[mode.index]);
            status.text = "Đã yêu cầu " + resolution.value + " · " + mode.value + ". Windows áp dụng vào cuối frame.";
        }
#else
        public void Initialize(VisualElement settings) { }
#endif
        public void Dispose() { bindings.Dispose(); owned?.RemoveFromHierarchy(); }
    }
}
