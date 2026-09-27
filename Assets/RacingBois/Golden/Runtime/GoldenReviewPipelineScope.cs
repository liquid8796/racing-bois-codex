using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Golden
{
    /// <summary>Applies an inspection-only pipeline while this review scene owns the override.</summary>
    [DisallowMultipleComponent]
    public sealed class GoldenReviewPipelineScope : MonoBehaviour
    {
        public RenderPipelineAsset Pipeline;
        private RenderPipelineAsset previous;
        private bool applied;

        private void OnEnable()
        {
            if (Pipeline == null) return;
            previous = QualitySettings.renderPipeline;
            QualitySettings.renderPipeline = Pipeline;
            applied = true;
        }

        private void OnDisable()
        {
            if (applied && QualitySettings.renderPipeline == Pipeline)
                QualitySettings.renderPipeline = previous;
            applied = false;
        }
    }
}
