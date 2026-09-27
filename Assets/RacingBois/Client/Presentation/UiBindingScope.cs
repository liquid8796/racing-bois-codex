using System;
using System.Collections.Generic;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    /// <summary>Owns callbacks installed on the longer-lived UIDocument. Dispose before replacing a view.</summary>
    internal sealed class UiBindingScope : IDisposable
    {
        private readonly List<Action> releases = new List<Action>();
        public void Click(Button button, Action action)
        {
            button.clicked += action;
            releases.Add(() => button.clicked -= action);
        }
        public void Register<T>(VisualElement element, EventCallback<T> callback, TrickleDown phase = TrickleDown.NoTrickleDown)
            where T : EventBase<T>, new()
        {
            element.RegisterCallback(callback, phase);
            releases.Add(() => element.UnregisterCallback(callback, phase));
        }
        public void Value<T>(BaseField<T> field, EventCallback<ChangeEvent<T>> callback)
        {
            field.RegisterValueChangedCallback(callback);
            releases.Add(() => field.UnregisterValueChangedCallback(callback));
        }
        public void Dispose()
        {
            for (int i = releases.Count - 1; i >= 0; i--) releases[i]();
            releases.Clear();
        }
    }
}
