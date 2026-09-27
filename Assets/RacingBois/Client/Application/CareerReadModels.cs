using System;
using System.Collections.Generic;
using RacingBois.Protocol;

namespace RacingBois.Client.Application
{
    /// <summary>A user intent contains no target profile, balance or price. The server resolves identity and all amounts.</summary>
    public sealed class CareerIntent
    {
        public string Operation { get; }
        public string BikeId { get; }
        public string CharacterId { get; }
        internal string Username { get; }
        internal string Password { get; }
        internal string RecoveryCode { get; }
        internal string SaveJson { get; }
        public CareerIntent(string operation = "view", string bikeId = "", string username = "", string password = "", string recoveryCode = "", string saveJson = "", string characterId = "")
        { Operation = operation; BikeId = bikeId; CharacterId = characterId; Username = username; Password = password; RecoveryCode = recoveryCode; SaveJson = saveJson; }
        internal CareerRequest ToRequest() => new CareerRequest { operation = Operation, bikeId = BikeId, characterId = CharacterId, username = Username,
            password = Password, recoveryCode = RecoveryCode, saveJson = SaveJson };
    }

    public sealed class CareerProfileReadModel
    {
        public string RealmId { get; } public string RealmKind { get; } public string ProfileId { get; }
        public string DisplayName { get; } public string Username { get; } public string SelectedBikeId { get; } public string SelectedCharacterId { get; }
        public int Credits { get; } public int LevelIndex { get; } public int QualificationMask { get; }
        public long Revision { get; } public bool CampaignComplete { get; }
        public IReadOnlyList<CareerOwnedBikeReadModel> Bikes { get; }
        internal CareerProfileReadModel(CareerProfileData data)
        {
            RealmId = data.realmId; RealmKind = data.realmKind; ProfileId = data.profileId; DisplayName = data.displayName;
            Username = data.username; SelectedBikeId = data.selectedBikeId; SelectedCharacterId = data.selectedCharacterId; Credits = data.credits; LevelIndex = data.levelIndex;
            QualificationMask = data.qualificationMask; Revision = data.revision; CampaignComplete = data.campaignComplete;
            var owned = new CareerOwnedBikeReadModel[data.bikes.Length];
            for (int i = 0; i < owned.Length; i++) owned[i] = new CareerOwnedBikeReadModel(data.bikes[i].bikeId, data.bikes[i].condition);
            Bikes = Array.AsReadOnly(owned);
        }
    }
    public sealed class CareerOwnedBikeReadModel
    {
        public string BikeId { get; } public int Condition { get; }
        internal CareerOwnedBikeReadModel(string id, int condition) { BikeId = id; Condition = condition; }
    }
    public sealed class CareerLedgerReadModel
    {
        public string TransactionId { get; } public string Reason { get; } public string BikeId { get; } public string CreatedUtc { get; }
        public int Delta { get; } public int Balance { get; }
        internal CareerLedgerReadModel(CareerLedgerEntry data)
        { TransactionId = data.transactionId; Reason = data.reason; BikeId = data.bikeId; CreatedUtc = data.createdUtc; Delta = data.delta; Balance = data.balance; }
    }
}
