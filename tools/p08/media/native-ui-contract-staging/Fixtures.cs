using System;
using System.Collections.Generic;
using System.Reflection;
using RacingBois.Client.Adapters;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

namespace RacingBois.Tools.NativeUi
{
    internal sealed class CareerWire : ICareerTransport
    {
        public Action<CareerResponse,bool> Callback;
        public void Send(string endpoint,string bearer,CareerRequest request,Action<CareerResponse,bool> callback) { Callback=callback; }
        public void Reply(CareerResponse response) => Callback(response,false);
        public static CareerResponse Profile() => new CareerResponse { ok=true,profile=new CareerProfileData { realmId="ui-realm",realmKind="offline",profileId="ui-profile",displayName="Player {route}",username="fixture-user",credits=1000,levelIndex=0,qualificationMask=0,revision=1,selectedBikeId=BikeCatalog.StarterBikeId,selectedCharacterId=CharacterCatalog.GetAt(0).Id,bikes=new[]{new CareerBikeData{bikeId=BikeCatalog.StarterBikeId,condition=100}} },ledger=Array.Empty<CareerLedgerEntry>() };
    }
    internal sealed class Store : IProfileCredentialStore,IResumeReceiptStore
    {
        private readonly Dictionary<string,ProfileCredential> data=new Dictionary<string,ProfileCredential>();
        public ProfileCredential Load(string endpoint)=>data.TryGetValue(endpoint,out var value)?value:null;
        public void Save(string endpoint,ProfileCredential value)=>data[endpoint]=value;
        public void Clear(string endpoint)=>data.Remove(endpoint);
        ResumeReceipt IResumeReceiptStore.Load(string endpoint)=>null;
        void IResumeReceiptStore.Save(string endpoint,ResumeReceipt value) { }
        void IResumeReceiptStore.Clear(string endpoint) { }
    }
    internal sealed class Clock : IMonotonicClock { public double NowSeconds=>1; }
    internal sealed class PacketWire : IRealtimeTransport
    {
        public event Action Opened; public event Action<string> Message; public event Action<string> Closed;
        public readonly UnityWireCodec Codec=new UnityWireCodec();public MpHello Hello;
        readonly Queue<string> messages=new Queue<string>();
        public void Connect(string endpoint)=>Opened?.Invoke();
        public void Send(string value) { if(Codec.Decode<MessageEnvelope>(value).kind=="mpHello")Hello=Codec.Decode<MpHello>(value); }
        public void Enqueue(object value)=>messages.Enqueue(Codec.Encode(value));
        public void Poll(){while(messages.Count>0)Message?.Invoke(messages.Dequeue());}
        public void Close()=>Closed?.Invoke("fixture closed");
        public void Dispose(){messages.Clear();Opened=null;Message=null;Closed=null;}
    }
    internal static class ReadModels
    {
        // Explicit synthetic presentation read state, projected by the installed application assembly.
        // No race authority, protocol acceptance or actual campaign outcome is claimed for these view inputs.
        public static RaceWorldReadModel World(long tick,long eventId)
        {
            var snapshot=new RaceSnapshotMessage { tick=tick,level=0,courseIndex=0,trackLengthMillimeters=2400000,
                riders=new[]{new RaceEntitySnapshot { id=1,kind=(int)RiderKind.Player,mode=(int)RiderMode.Riding,weapon=(int)WeaponKind.Fist,attackWeapon=(int)WeaponKind.Fist,health=4096,bikeCondition=100,strength=7,rank=1,finishTick=-1,gear=1,speedMillimetersPerSecond=10000 }},
                traffic=Array.Empty<RaceTrafficSnapshot>(),pedestrians=Array.Empty<RacePedestrianSnapshot>() };
            var assembly=typeof(RaceWorldReadModel).Assembly;
            var projection=assembly.GetType("RacingBois.Client.Application.RaceStateProjection",true);
            var world=(RaceWorldReadModel)projection.GetMethod("World",BindingFlags.Public|BindingFlags.Static,null,new[]{typeof(RaceSnapshotMessage)},null).Invoke(null,new object[]{snapshot});
            var constructor=typeof(RaceEventReadModel).GetConstructor(BindingFlags.NonPublic|BindingFlags.Instance,null,new[]{typeof(long),typeof(long),typeof(RaceEventKind),typeof(int),typeof(int),typeof(int)},null);
            var evt=(RaceEventReadModel)constructor.Invoke(new object[]{eventId,tick,RaceEventKind.Hit,1,2,1});
            return (RaceWorldReadModel)assembly.GetType("RacingBois.Client.Application.MultiplayerProjection",true).GetMethod("Copy",BindingFlags.Public|BindingFlags.Static).Invoke(null,new object[]{world,new[]{evt}});
        }
    }
}
