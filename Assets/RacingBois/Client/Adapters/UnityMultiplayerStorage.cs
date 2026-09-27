using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using RacingBois.Client.Application;
using UnityEngine;

namespace RacingBois.Client.Adapters
{
    public sealed class UnityMonotonicClock : IMonotonicClock
    {
        public double NowSeconds => Time.realtimeSinceStartupAsDouble;
    }

    /// <summary>Cosmetic local settings, durable host credentials and tab-scoped resume leases are separate stores.</summary>
    public sealed class UnityMultiplayerStorage : IPlayerProfileStore, IResumeReceiptStore, IProfileCredentialStore
    {
        private readonly Dictionary<string,string> editorTabStorage = new Dictionary<string,string>();
        private readonly Dictionary<string,string> browserFallback = new Dictionary<string,string>();
        public bool PersistenceAvailable { get; private set; } = true;
        public bool ResumeStorageAvailable { get; private set; } = true;
#if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern IntPtr RB_StorageRead(string key, int persistent);
        [DllImport("__Internal")] private static extern int RB_StorageWrite(string key, string value, int persistent);
        [DllImport("__Internal")] private static extern void RB_StorageRemove(string key, int persistent);
        [DllImport("__Internal")] private static extern void RB_StorageFree(IntPtr value);
#endif
        [Serializable] private sealed class CosmeticDto { public string id, name; public int color; }
        [Serializable] private sealed class ResumeDto { public string roomId, code, playerId, token; }
        [Serializable] private sealed class CredentialDto { public string token, id, name, realm; public int credits; }
        public LocalPlayerProfile LoadOrCreate()
        {
            CosmeticDto value = Read<CosmeticDto>("rb.profile.cosmetic.v1", true);
            if(value == null || string.IsNullOrEmpty(value.id) || value.id.Length > 64 || string.IsNullOrWhiteSpace(value.name))
            {
                var profile = new LocalPlayerProfile(Guid.NewGuid().ToString("N"), "Tay đua", 0);
                Save(profile); return profile;
            }
            return new LocalPlayerProfile(value.id, value.name, Mathf.Clamp(value.color,0,7));
        }
        public void Save(LocalPlayerProfile profile)
        {
            Write("rb.profile.cosmetic.v1",JsonUtility.ToJson(new CosmeticDto {id=profile.ProfileId,name=profile.DisplayName,color=profile.ColorIndex}),true);
        }
        ResumeReceipt IResumeReceiptStore.Load(string endpoint)
        {
            if(string.IsNullOrEmpty(endpoint))return null;
            var value=Read<ResumeDto>(Key("resume",endpoint),false);
            return value==null || string.IsNullOrEmpty(value.token) ? null :
                new ResumeReceipt(value.roomId,value.code,value.playerId,value.token);
        }
        void IResumeReceiptStore.Save(string endpoint,ResumeReceipt receipt)
        {
            Write(Key("resume",endpoint),JsonUtility.ToJson(new ResumeDto
                {roomId=receipt.RoomId,code=receipt.RoomCode,playerId=receipt.PlayerId,token=receipt.ResumeToken}),false);
        }
        void IResumeReceiptStore.Clear(string endpoint) { if(!string.IsNullOrEmpty(endpoint))Remove(Key("resume",endpoint),false); }
        ProfileCredential IProfileCredentialStore.Load(string endpoint)
        {
            if(string.IsNullOrEmpty(endpoint))return null;
            var value=Read<CredentialDto>(Key("credential",endpoint),true);
            return value==null || string.IsNullOrEmpty(value.token) ? null :
                new ProfileCredential(value.token,value.id,value.name,value.realm,value.credits);
        }
        void IProfileCredentialStore.Save(string endpoint,ProfileCredential credential)
        {
            Write(Key("credential",endpoint),JsonUtility.ToJson(new CredentialDto
                {token=credential.ProfileToken,id=credential.ProfileId,name=credential.DisplayName,realm=credential.RealmId,credits=credential.Credits}),true);
        }
        void IProfileCredentialStore.Clear(string endpoint) { if(!string.IsNullOrEmpty(endpoint))Remove(Key("credential",endpoint),true); }
        private static string Key(string kind,string endpoint)
        {
            if(!Uri.TryCreate(endpoint,UriKind.Absolute,out var uri) || (uri.Scheme!="ws" && uri.Scheme!="wss") || !string.IsNullOrEmpty(uri.UserInfo))
                throw new ArgumentException("A WebSocket endpoint without embedded credentials is required.");
            return "rb."+kind+".v1."+Uri.EscapeDataString(uri.AbsoluteUri);
        }
        private T Read<T>(string key,bool persistent) where T:class
        {
            string text="";
#if UNITY_WEBGL && !UNITY_EDITOR
            bool available=persistent?PersistenceAvailable:ResumeStorageAvailable;
            if(!available&&browserFallback.TryGetValue(key,out text)) { }
            else
            {
                IntPtr pointer=RB_StorageRead(key,persistent?1:0);
                if(pointer!=IntPtr.Zero)
                {
                    try {text=Marshal.PtrToStringUTF8(pointer);}
                    finally {RB_StorageFree(pointer);}
                }
                else
                {
                    if(persistent)PersistenceAvailable=false;else ResumeStorageAvailable=false;
                    browserFallback.TryGetValue(key,out text);
                }
            }
#else
            if(persistent) text=PlayerPrefs.GetString(key,"");
            else editorTabStorage.TryGetValue(key,out text);
#endif
            if(string.IsNullOrEmpty(text) || text.Length>8192)return null;
            try {return JsonUtility.FromJson<T>(text);} catch(ArgumentException){return null;}
        }
        private void Write(string key,string value,bool persistent)
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            browserFallback[key]=value;
            if(RB_StorageWrite(key,value,persistent?1:0)==0)
            {if(persistent)PersistenceAvailable=false;else ResumeStorageAvailable=false;}
#else
            if(persistent){PlayerPrefs.SetString(key,value);PlayerPrefs.Save();}
            else editorTabStorage[key]=value;
#endif
        }
        private void Remove(string key,bool persistent)
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_StorageRemove(key,persistent?1:0);
            browserFallback.Remove(key);
#else
            if(persistent){PlayerPrefs.DeleteKey(key);PlayerPrefs.Save();}
            else editorTabStorage.Remove(key);
#endif
        }
    }
}
