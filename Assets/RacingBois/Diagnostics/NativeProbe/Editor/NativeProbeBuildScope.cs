using System;
using System.Collections.Generic;

namespace RacingBois.Diagnostics.NativeProbe.Editor
{
    /// <summary>Restores only explicitly registered probe mutations; independent cleanup survives individual failures.</summary>
    internal sealed class NativeProbeBuildScope
    {
        private readonly List<KeyValuePair<string, Action>> restore = new List<KeyValuePair<string, Action>>();
        private bool restored;
        public bool SettingsChanged { get; private set; }
        public void ChangeSetting(string name, Action apply, Action undo)
        {
            if (restored) throw new InvalidOperationException("scope_already_restored");
            if (apply == null || undo == null) throw new ArgumentNullException(nameof(apply));
            // Arm rollback before the setter: a platform setter may change state and then throw.
            restore.Add(new KeyValuePair<string, Action>(name, undo)); SettingsChanged = true; apply();
        }
        public void Own(string name, Action cleanup)
        {
            if (restored) throw new InvalidOperationException("scope_already_restored");
            restore.Add(new KeyValuePair<string, Action>(name, cleanup ?? throw new ArgumentNullException(nameof(cleanup))));
        }
        public string[] Restore()
        {
            if (restored) return Array.Empty<string>();
            restored = true; var failures = new List<string>();
            for (int i = restore.Count - 1; i >= 0; i--)
                try { restore[i].Value(); }
                catch (Exception error) { failures.Add(restore[i].Key + ":" + error.GetType().Name); }
            restore.Clear(); return failures.ToArray();
        }
    }
}
