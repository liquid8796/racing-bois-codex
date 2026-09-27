using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    /// <summary>Small view helpers shared by the race and lobby. No application state is owned here.</summary>
    internal static class UiViewState
    {
        public static bool Visible(VisualElement element) => element != null && element.style.display.value != DisplayStyle.None;

        public static void Show(VisualElement element, bool visible)
        {
            if (element == null || Visible(element) == visible) return;
            element.style.display = visible ? DisplayStyle.Flex : DisplayStyle.None;
            if (!visible) { element.RemoveFromClassList("panel-enter"); return; }
            // This runs only when a panel changes state, never for every snapshot or frame.
            element.AddToClassList("panel-enter");
            element.schedule.Execute(() => element.RemoveFromClassList("panel-enter")).StartingIn(16);
        }

        public static void Text(TextElement element, string value)
        {
            if (element.text != value) element.text = value;
        }

        public static bool HasTextFocus(VisualElement root)
        {
            var focused = root?.panel?.focusController.focusedElement as VisualElement;
            while (focused != null)
            {
                if (focused is TextField) return true;
                focused = focused.parent;
            }
            return false;
        }
    }
}
