using System.Collections.Generic;
using RacingBois.Client.Application;

namespace RacingBois.Diagnostics.NativeProbe
{
    /// <summary>One probe lifetime only. Never accesses PlayerPrefs, files or existing player credentials.</summary>
    internal sealed class NativeProbeMemoryStore : IResumeReceiptStore, IProfileCredentialStore
    {
        private readonly Dictionary<string, ResumeReceipt> resumes = new Dictionary<string, ResumeReceipt>();
        private readonly Dictionary<string, ProfileCredential> credentials = new Dictionary<string, ProfileCredential>();
        ResumeReceipt IResumeReceiptStore.Load(string endpoint) => resumes.TryGetValue(endpoint, out var value) ? value : null;
        void IResumeReceiptStore.Save(string endpoint, ResumeReceipt receipt) => resumes[endpoint] = receipt;
        void IResumeReceiptStore.Clear(string endpoint) => resumes.Remove(endpoint);
        ProfileCredential IProfileCredentialStore.Load(string endpoint) => credentials.TryGetValue(endpoint, out var value) ? value : null;
        void IProfileCredentialStore.Save(string endpoint, ProfileCredential credential) => credentials[endpoint] = credential;
        void IProfileCredentialStore.Clear(string endpoint) => credentials.Remove(endpoint);
        public void Clear() { resumes.Clear(); credentials.Clear(); }
    }
}
