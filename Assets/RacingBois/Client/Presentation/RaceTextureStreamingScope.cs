using System;
using UnityEngine;

namespace RacingBois.Client.Presentation
{
    /// <summary>Owns runtime streaming settings and restores only values still held by this scope.</summary>
    internal sealed class RaceTextureStreamingScope : IDisposable
    {
        private readonly bool originalActive = QualitySettings.streamingMipmapsActive;
        private readonly float originalBudget = QualitySettings.streamingMipmapsMemoryBudget;
        private readonly int originalReduction = QualitySettings.streamingMipmapsMaxLevelReduction;
        private bool applied, disposed;
        private float budget;
        private int reduction;

        public void Apply(int index)
        {
            if (disposed) throw new ObjectDisposedException(nameof(RaceTextureStreamingScope));
            index = Mathf.Clamp(index, 0, 2);
            budget = index == 0 ? 256 : index == 1 ? 512 : 768;
            reduction = index == 0 ? 3 : 2;
            QualitySettings.streamingMipmapsActive = true;
            QualitySettings.streamingMipmapsMemoryBudget = budget;
            QualitySettings.streamingMipmapsMaxLevelReduction = reduction;
            applied = true;
        }

        public void Dispose()
        {
            if (disposed) return;
            disposed = true;
            if (!applied) return;
            if (QualitySettings.streamingMipmapsActive) QualitySettings.streamingMipmapsActive = originalActive;
            if (QualitySettings.streamingMipmapsMemoryBudget == budget) QualitySettings.streamingMipmapsMemoryBudget = originalBudget;
            if (QualitySettings.streamingMipmapsMaxLevelReduction == reduction) QualitySettings.streamingMipmapsMaxLevelReduction = originalReduction;
        }
    }
}
