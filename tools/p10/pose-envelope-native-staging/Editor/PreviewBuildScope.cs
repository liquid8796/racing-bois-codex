using System;
using System.Collections.Generic;

namespace RacingBois.Diagnostics.PoseEnvelopePreview.Editor
{
    internal sealed class PreviewBuildScope
    {
        private readonly List<KeyValuePair<string,Action>> journal=new List<KeyValuePair<string,Action>>();private bool restored;
        internal bool Changed{get;private set;}
        internal void Own(string name,Action undo)
        {if(restored)throw new InvalidOperationException("scope_restored");journal.Add(new KeyValuePair<string,Action>(name,undo??throw new ArgumentNullException(nameof(undo))));}
        internal void Change(string name,Action apply,Action undo)
        {Own(name,undo);Changed=true;apply();}
        internal string[] Restore()
        {
            if(restored)return Array.Empty<string>();restored=true;var failures=new List<string>();
            for(int i=journal.Count-1;i>=0;i--)try{journal[i].Value();}catch(Exception e){failures.Add(journal[i].Key+":"+e.GetType().Name);}
            journal.Clear();return failures.ToArray();
        }
    }
}
