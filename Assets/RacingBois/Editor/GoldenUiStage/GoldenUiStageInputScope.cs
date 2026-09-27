#if UNITY_EDITOR
using System;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Block original menu intents without changing their visual enabled state.</summary>
    internal sealed class GoldenUiStageInputScope : IDisposable
    {
        private readonly VisualElement root, toolbar;
        private readonly Func<VisualElement> garage;
        private readonly Action close;
        internal GoldenUiStageInputScope(VisualElement root, VisualElement toolbar, Func<VisualElement> garage, Action close)
        {
            this.root = root; this.toolbar = toolbar; this.garage = garage; this.close = close;
            root.RegisterCallback<PointerDownEvent>(PointerDown, TrickleDown.TrickleDown);
            root.RegisterCallback<PointerUpEvent>(PointerUp, TrickleDown.TrickleDown);
            root.RegisterCallback<ClickEvent>(Click, TrickleDown.TrickleDown);
            root.RegisterCallback<NavigationSubmitEvent>(Submit, TrickleDown.TrickleDown);
            root.RegisterCallback<KeyDownEvent>(Key, TrickleDown.TrickleDown);
        }
        private bool Allowed(object value)
        {
            var target = value as VisualElement;
            if (target == null) return false;
            var overlay = garage();
            return target == toolbar || toolbar.Contains(target) || overlay != null && (target == overlay || overlay.Contains(target));
        }
        private void PointerDown(PointerDownEvent e) { if (!Allowed(e.target)) e.StopImmediatePropagation(); }
        private void PointerUp(PointerUpEvent e) { if (!Allowed(e.target)) e.StopImmediatePropagation(); }
        private void Click(ClickEvent e) { if (!Allowed(e.target)) e.StopImmediatePropagation(); }
        private void Submit(NavigationSubmitEvent e) { if (!Allowed(e.target)) e.StopImmediatePropagation(); }
        private void Key(KeyDownEvent e)
        {
            if (Allowed(e.target) || e.keyCode == KeyCode.Tab) return;
            e.StopImmediatePropagation();
            if (e.keyCode == KeyCode.Escape) close();
        }
        public void Dispose()
        {
            root.UnregisterCallback<PointerDownEvent>(PointerDown, TrickleDown.TrickleDown);
            root.UnregisterCallback<PointerUpEvent>(PointerUp, TrickleDown.TrickleDown);
            root.UnregisterCallback<ClickEvent>(Click, TrickleDown.TrickleDown);
            root.UnregisterCallback<NavigationSubmitEvent>(Submit, TrickleDown.TrickleDown);
            root.UnregisterCallback<KeyDownEvent>(Key, TrickleDown.TrickleDown);
        }
    }
}
#endif
