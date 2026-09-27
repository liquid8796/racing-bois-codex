using System;
using System.Collections;
using System.Collections.Generic;
using RacingBois.Client.Application;
using UnityEngine;

namespace RacingBois.Client.Presentation
{
    [Serializable]
    public sealed class CinematicDirectorReport
    {
        public bool passed; public int sequences, frames; public List<CinematicFrameCheck> checks = new List<CinematicFrameCheck>();
        public List<string> failures = new List<string>();
        public string scope = "Actual cloned production actors, imported clip samples, renderer references/bounds and camera transforms. Visual framing/story quality remains separate human QA.";
    }
    public static class CinematicValidationHarness
    {
        /// <summary>Run in Play mode after actor/route loading; yields between sequences so destroyed objects are released.</summary>
        public static IEnumerator EvaluateAll(CinematicDirector director, Action<CinematicDirectorReport> completed)
        {
            var report = new CinematicDirectorReport();
            if (director == null) { report.failures.Add("missing-director"); completed?.Invoke(report); yield break; }
            foreach (var sequence in CinematicCatalog.All)
            {
                if (!director.StartPlayback(sequence)) { report.failures.Add(sequence.Id + ": " + director.LastError); continue; }
                report.sequences++;
                foreach (var beat in sequence.Beats)
                {
                    foreach (float phase in new[] { 0f, .5f, .999f })
                    {
                        director.Evaluate(beat.StartSeconds + beat.DurationSeconds * phase);
                        var frame = director.InspectCurrentFrame(); report.checks.Add(frame); report.frames++;
                        if (!frame.passed) report.failures.Add(sequence.Id + " at " + frame.time);
                    }
                }
                director.Stop(true);
                if (director.OwnedActorCount != 0 || director.OwnedPropCount != 0) report.failures.Add("owned-objects-retained");
                yield return null;
            }
            report.passed = report.failures.Count == 0 && report.sequences == 59 && report.frames == 1167;
            completed?.Invoke(report);
        }
    }
}
