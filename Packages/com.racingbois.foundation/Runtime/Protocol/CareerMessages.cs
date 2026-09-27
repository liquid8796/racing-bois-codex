using System;

namespace RacingBois.Protocol
{
    // HTTP career commands never accept a target profile or a client supplied amount.
    [Serializable] public sealed class CareerRequest
    {
        public string operation = "view", transactionId = "", bikeId = "", characterId = "";
        public string username = "", password = "", recoveryCode = "", saveJson = "";
    }
    [Serializable] public sealed class CareerResponse
    {
        public bool ok;
        public string code = "", profileToken = "", recoveryCode = "", exportJson = "";
        public CareerProfileData profile = new CareerProfileData();
        public CareerLedgerEntry[] ledger = new CareerLedgerEntry[0];
    }
    [Serializable] public sealed class CareerProfileData
    {
        public string realmId = "", realmKind = "", profileId = "", displayName = "", username = "", selectedBikeId = "";
        public string selectedCharacterId = "rb-ash";
        public int credits, levelIndex, qualificationMask;
        public long revision;
        public bool campaignComplete;
        public CareerBikeData[] bikes = new CareerBikeData[0];
    }
    [Serializable] public sealed class CareerBikeData
    { public string bikeId = ""; public int condition = 100; }
    [Serializable] public sealed class CareerLedgerEntry
    { public string transactionId = "", reason = "", bikeId = "", createdUtc = ""; public int delta, balance; }
}
