namespace RacingBois.Client.Application
{
    /// <summary>Temporary local session progress. This is not the online account balance.</summary>
    public readonly struct LocalCampaignReadModel
    {
        public int Level { get; }
        public int QualifiedCourseMask { get; }
        public int Credits { get; }
        public bool Completed { get; }
        public long LastAppliedRunId { get; }
        internal LocalCampaignReadModel(int level, int qualifiedCourseMask, int credits, bool completed, long lastAppliedRunId)
        { Level = level; QualifiedCourseMask = qualifiedCourseMask; Credits = credits; Completed = completed; LastAppliedRunId = lastAppliedRunId; }
    }
}
