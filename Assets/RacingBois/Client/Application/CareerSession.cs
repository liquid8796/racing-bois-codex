using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

namespace RacingBois.Client.Application
{
    public interface ICareerTransport
    {
        void Send(string endpoint, string bearer, CareerRequest request, Action<CareerResponse, bool> completed);
    }

    /// <summary>One in-flight intent, authoritative responses and endpoint-scoped credentials. No currency is mutated locally.</summary>
    public sealed class CareerSession
    {
        private readonly ICareerTransport transport;
        private readonly IProfileCredentialStore credentials;
        private readonly IResumeReceiptStore leases;
        private CareerRequest retry;
        private string endpoint = "";
        private int generation;
        public event Action Changed;
        public CareerProfileReadModel Profile { get; private set; }
        public IReadOnlyList<CareerLedgerReadModel> Ledger { get; private set; } = Array.AsReadOnly(new CareerLedgerReadModel[0]);
        public string ErrorCode { get; private set; } = "";
        public string Notice { get; private set; } = "";
        public string RecoveryCode { get; private set; } = "";
        public string ExportJson { get; private set; } = "";
        public bool Busy { get; private set; }
        public bool CanRetry => !Busy && retry != null;
        public bool HasCredential => !string.IsNullOrEmpty(endpoint) && credentials.Load(endpoint) != null;
        public string Endpoint => endpoint;

        public CareerSession(ICareerTransport transport, IProfileCredentialStore credentials, IResumeReceiptStore leases)
        { this.transport = transport; this.credentials = credentials; this.leases = leases; }

        public void SetEndpoint(string value)
        {
            string normalized = NormalizeEndpoint(value);
            if (endpoint == normalized) return;
            generation++; endpoint = normalized; Busy = false; retry = null; Profile = null;
            Ledger = Array.AsReadOnly(new CareerLedgerReadModel[0]); ErrorCode = Notice = RecoveryCode = ExportJson = "";
            Changed?.Invoke();
        }
        public void Refresh() => Execute(new CareerIntent());
        public void Retry()
        {
            if (!CanRetry) return;
            var sameIntent = retry; retry = null; Send(sameIntent);
        }
        public void ClearSensitiveOutput() { RecoveryCode = ExportJson = ""; Changed?.Invoke(); }
        public void ClearView()
        {
            if (Busy) return;
            Profile = null; Ledger = Array.AsReadOnly(new CareerLedgerReadModel[0]);
            RecoveryCode = ExportJson = Notice = ErrorCode = ""; retry = null; Changed?.Invoke();
        }
        public void Execute(CareerIntent intent)
        {
            if (Busy || intent == null) return;
            var request = intent.ToRequest();
            retry = null; RecoveryCode = ExportJson = Notice = ErrorCode = "";
            bool auth = request.operation == "login" || request.operation == "recover";
            if (string.IsNullOrEmpty(endpoint)) { Fail("endpoint_required"); return; }
            if (request.operation == "forget")
            {
                credentials.Clear(endpoint); leases.Clear(endpoint); Profile = null;
                Ledger = Array.AsReadOnly(new CareerLedgerReadModel[0]); Notice = "forget"; Changed?.Invoke(); return;
            }
            if (!auth && !HasCredential) { Fail("auth_required"); return; }
            if (IsPasswordOperation(request.operation) && !endpoint.StartsWith("wss://", StringComparison.Ordinal))
            { request.password = request.recoveryCode = ""; Fail("https_required"); return; }
            request.transactionId = Guid.NewGuid().ToString("D");
            Send(request);
        }
        private void Send(CareerRequest request)
        {
            Busy = true; ErrorCode = ""; Changed?.Invoke();
            int issuedGeneration = generation;
            string bearer = credentials.Load(endpoint)?.ProfileToken ?? "";
            transport.Send(ApiEndpoint(endpoint), bearer, request, (response, transient) =>
            {
                request.password = request.recoveryCode = "";
                if (issuedGeneration != generation) return;
                Busy = false;
                if (response == null || !response.ok)
                {
                    ErrorCode = response?.code ?? "network_unavailable";
                    if (transient && !IsPasswordOperation(request.operation)) retry = request;
                    Changed?.Invoke(); return;
                }
                retry = null; Notice = request.operation;
                if (request.operation == "logout" || request.operation == "logoutAll")
                { credentials.Clear(endpoint); leases.Clear(endpoint); Profile = null; Ledger = Array.AsReadOnly(new CareerLedgerReadModel[0]); }
                else if (response.profile != null && !string.IsNullOrEmpty(response.profile.profileId))
                {
                    if (!ValidProfile(response.profile)) { ErrorCode = "invalid_response"; Changed?.Invoke(); return; }
                    Profile = new CareerProfileReadModel(response.profile);
                    var rows = response.ledger ?? new CareerLedgerEntry[0];
                    var projection = new CareerLedgerReadModel[Math.Min(rows.Length, 200)];
                    for (int i = 0; i < projection.Length; i++) projection[i] = new CareerLedgerReadModel(rows[i] ?? new CareerLedgerEntry());
                    Ledger = Array.AsReadOnly(projection);
                    string token = string.IsNullOrEmpty(response.profileToken) ? bearer : response.profileToken;
                    if (!string.IsNullOrEmpty(response.profileToken)) leases.Clear(endpoint);
                    if (!string.IsNullOrEmpty(token)) credentials.Save(endpoint, new ProfileCredential(token,
                        Profile.ProfileId, Profile.DisplayName, Profile.RealmId, Profile.Credits));
                }
                RecoveryCode = response.recoveryCode ?? ""; ExportJson = response.exportJson ?? "";
                Changed?.Invoke();
            });
        }
        private static bool ValidProfile(CareerProfileData profile)
        {
            if (profile.credits < 0 || profile.levelIndex < 0 || profile.levelIndex >= CampaignCatalog.LevelCount ||
                profile.qualificationMask < 0 || profile.qualificationMask > 31 || string.IsNullOrEmpty(profile.realmId) ||
                string.IsNullOrEmpty(profile.realmKind) || profile.bikes == null || profile.bikes.Length == 0 || profile.bikes.Length > BikeCatalog.Count) return false;
            var ids = new HashSet<string>();
            foreach (var bike in profile.bikes)
                if (bike == null || !BikeCatalog.TryGet(bike.bikeId, out _) || !ids.Add(bike.bikeId) || bike.condition < 0 || bike.condition > 100) return false;
            return ids.Contains(profile.selectedBikeId) && CharacterCatalog.TryGet(profile.selectedCharacterId, out _);
        }
        private void Fail(string code) { ErrorCode = code; Changed?.Invoke(); }
        public static bool IsPasswordOperation(string operation) => operation == "register" || operation == "login" || operation == "recover" || operation == "rotateRecovery";
        public static bool ChangesIdentity(string operation) => IsPasswordOperation(operation) || operation == "logout" || operation == "logoutAll" || operation == "forget";
        public static string NormalizeEndpoint(string value)
        {
            if (!Uri.TryCreate(value, UriKind.Absolute, out var uri) || (uri.Scheme != "ws" && uri.Scheme != "wss") ||
                !string.IsNullOrEmpty(uri.UserInfo) || !string.IsNullOrEmpty(uri.Fragment) || !string.IsNullOrEmpty(uri.Query))
                throw new ArgumentException("Cần địa chỉ ws:// hoặc wss:// hợp lệ, không chứa thông tin đăng nhập.");
            return uri.AbsoluteUri;
        }
        public static string ApiEndpoint(string value)
        { var uri = new Uri(NormalizeEndpoint(value)); return (uri.Scheme == "wss" ? "https://" : "http://") + uri.Authority + "/api/career"; }
        public static string InviteCode(string pageUrl)
        {
            if (!Uri.TryCreate(pageUrl, UriKind.Absolute, out var page)) return "";
            foreach (var part in page.Query.TrimStart('?').Split('&'))
            {
                if (!part.StartsWith("room=", StringComparison.Ordinal)) continue;
                string code = Uri.UnescapeDataString(part.Substring(5)).ToUpperInvariant();
                if (code.Length != 6) return "";
                foreach (char c in code) if (!(c >= 'A' && c <= 'Z') && !(c >= '0' && c <= '9')) return "";
                return code;
            }
            return "";
        }
    }
}
