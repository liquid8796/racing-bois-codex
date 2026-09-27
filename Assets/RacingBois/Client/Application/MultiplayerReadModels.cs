using System;
using System.Collections.Generic;

namespace RacingBois.Client.Application
{
    public enum LobbyPhase { Lobby, Countdown, Racing, Results, Closing }
    public enum RaceOutcome { Racing, Finished, Wrecked, Busted, Dnf }
    public sealed class LobbyOptions
    {
        public string Name { get; } public int BotCount { get; }
        public bool PublicRoom { get; } public int CourseIndex { get; } public int LevelIndex { get; }
        public LobbyOptions(string name, int botCount = 5, bool publicRoom = true, int courseIndex = 0, int levelIndex = 0)
        { Name = name ?? ""; BotCount = botCount; PublicRoom = publicRoom; CourseIndex = courseIndex; LevelIndex = levelIndex; }
    }
    public sealed class LobbyMemberReadModel
    {
        public string PlayerId { get; } public string DisplayName { get; } public int RiderId { get; }
        public bool Ready { get; } public bool Connected { get; } public bool Guest { get; }
        internal LobbyMemberReadModel(string id, string name, int riderId, bool ready, bool connected, bool guest)
        { PlayerId = id; DisplayName = name; RiderId = riderId; Ready = ready; Connected = connected; Guest = guest; }
    }
    public sealed class LobbyReadModel
    {
        public string RoomId { get; } public string Code { get; } public string Name { get; }
        public string HostPlayerId { get; } public string MatchId { get; }
        public LobbyPhase Phase { get; } public int Revision { get; } public int RaceEpoch { get; }
        public int BotCount { get; } public int MaxPlayers { get; } public long StartServiceTick { get; }
        public bool PublicRoom { get; } public int CourseIndex { get; } public int LevelIndex { get; }
        public IReadOnlyList<LobbyMemberReadModel> Members { get; }
        internal LobbyReadModel(string id, string code, string name, string host, string match, LobbyPhase phase,
            int revision, int epoch, int bots, int maxPlayers, long start, LobbyMemberReadModel[] members, bool publicRoom = true, int courseIndex = 0, int levelIndex = 0)
        {
            RoomId = id; Code = code; Name = name; HostPlayerId = host; MatchId = match; Phase = phase;
            Revision = revision; RaceEpoch = epoch; BotCount = bots; MaxPlayers = maxPlayers; StartServiceTick = start;
            PublicRoom = publicRoom; CourseIndex = courseIndex; LevelIndex = levelIndex;
            Members = Array.AsReadOnly((LobbyMemberReadModel[])members.Clone());
        }
    }
    public sealed class LobbySummaryReadModel
    {
        public string Code { get; } public string Name { get; } public int Players { get; } public int MaxPlayers { get; } public LobbyPhase Phase { get; }
        public bool PublicRoom { get; } public int CourseIndex { get; } public int LevelIndex { get; }
        internal LobbySummaryReadModel(string code, string name, int players, int max, LobbyPhase phase, bool publicRoom = true, int courseIndex = 0, int levelIndex = 0)
        { Code = code; Name = name; Players = players; MaxPlayers = max; Phase = phase; PublicRoom = publicRoom; CourseIndex = courseIndex; LevelIndex = levelIndex; }
    }
    public sealed class MultiplayerResultEntry
    {
        public string PlayerId { get; } public string DisplayName { get; } public int RiderId { get; }
        public RaceOutcome Outcome { get; } public int Rank { get; } public int Reward { get; } public int Credits { get; } public long FinishTick { get; }
        internal MultiplayerResultEntry(string player, string name, int rider, RaceOutcome outcome, int rank, int reward, int credits, long finish)
        { PlayerId = player; DisplayName = name; RiderId = rider; Outcome = outcome; Rank = rank; Reward = reward; Credits = credits; FinishTick = finish; }
    }
    public sealed class MultiplayerResultReadModel
    {
        public string ResultId { get; } public string MatchId { get; } public bool Persisted { get; }
        public IReadOnlyList<MultiplayerResultEntry> Entries { get; }
        internal MultiplayerResultReadModel(string id, string match, bool persisted, MultiplayerResultEntry[] entries)
        { ResultId = id; MatchId = match; Persisted = persisted; Entries = Array.AsReadOnly((MultiplayerResultEntry[])entries.Clone()); }
    }
    public readonly struct MultiplayerStandingReadModel
    {
        public int RiderId { get; } public int Rank { get; } public RaceOutcome Outcome { get; } public float DistanceMeters { get; }
        internal MultiplayerStandingReadModel(int id, int rank, RaceOutcome outcome, float distance)
        { RiderId = id; Rank = rank; Outcome = outcome; DistanceMeters = distance; }
    }
}
