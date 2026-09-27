using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
namespace RacingBois.Client.Application
{
    public sealed class P08AudioRole
    {
        public string Id { get; } public string Hook { get; } public bool Loop { get; }
        internal P08AudioRole(string id,string hook,bool loop=false){Id=id;Hook=hook;Loop=loop;}
    }
    /// <summary>Deterministic presentation cue selection. No sound changes authority or combat results.</summary>
    public static class P08AudioRoles
    {
        private static readonly string[] engineByBike={"street-single-engine","street-single-engine","street-single-engine","sport-twin-engine","street-single-engine","apex-four-engine","apex-four-engine","apex-four-engine","apex-four-engine","apex-four-engine","sport-twin-engine","sport-twin-engine","sport-twin-engine","engine-touring","sport-twin-engine"};
        // Columns are Attack, Hit, Crash, Finished, Remounted, Busted. Kai's five authored reactions deliberately share its protest cue.
        private static readonly string[][] reactions={
            new[]{"ash-effort-hard","ash-concern","ash-alert","ash-victory","ash-cheer","ash-refuse"},
            new[]{"juno-effort-soft","juno-surprise","juno-panic","juno-lookout","juno-retort","juno-alarm"},
            new[]{"mako-effort-deep","mako-tease","mako-warning","mako-greeting","mako-attention","mako-stop"},
            new[]{"rook-effort-burst","rook-startle","rook-caution","rook-amused","rook-question","rook-warning"},
            new[]{"sol-effort","sol-question","sol-effort-long","sol-challenge","sol-hold","sol-slow"},
            new[]{"vale-effort-low","vale-startle","vale-tourist-alarm","vale-ready","vale-help","vale-step-back"},
            new[]{"echo-effort-high","echo-shock","echo-disbelief","echo-rev","echo-step-aside","echo-refusal"},
            new[]{"kai-effort-short","kai-surprise","kai-confusion","kai-wait","kai-protest","kai-protest"}
        };
        public static string Engine(int bikeIndex){BikeCatalog.GetAt(bikeIndex);return engineByBike[bikeIndex];}
        public static string Attack(WeaponKind weapon)=>weapon==WeaponKind.Chain?"chain-air-sweep":"glove-air-sweep";
        public static string Hit(WeaponKind weapon,long eventId)
        {switch(weapon){case WeaponKind.Kick:return "boot-side-contact";case WeaponKind.Club:return "wood-grip-contact";case WeaponKind.Chain:return "chain-link-contact";default:return (eventId&1)==0?"glove-contact-light":"glove-contact-heavy";}}
        public static string Crash(int severity,bool wrecked)=>wrecked||severity>500?"crash-barrier-heavy":severity<=350?"crash-shoulder-light":"crash-traffic-medium";
        public static string Reaction(int characterIndex,RaceEventKind kind)
        {
            CharacterCatalog.GetAt(characterIndex);int slot;
            switch(kind){case RaceEventKind.Attack:slot=0;break;case RaceEventKind.Hit:slot=1;break;case RaceEventKind.Crash:case RaceEventKind.Wrecked:slot=2;break;
                case RaceEventKind.Finished:slot=3;break;case RaceEventKind.Remounted:slot=4;break;case RaceEventKind.Busted:slot=5;break;default:return "";}
            return reactions[characterIndex][slot];
        }
        public static IReadOnlyList<P08AudioRole> All {get;}=BuildRoles();
        private static IReadOnlyList<P08AudioRole> BuildRoles()
        {
            var roles=new List<P08AudioRole>();var ids=new HashSet<string>(StringComparer.Ordinal);
            Action<string,string,bool> add=(id,hook,loop)=>{if(ids.Add(id))roles.Add(new P08AudioRole(id,hook,loop));};
            foreach(var id in engineByBike)add(id,"selected bike engine loop",true);
            add("boost-pressure","high RPM engine layer",true);add("opponent-engine","nearest opponent engine",true);add("traffic-four-cylinder","nearest traffic engine",true);
            add("tunnel-engine-resonance","Ridge gallery proximity layer",true);add("patrol-long-call","police within32m",true);add("patrol-short-call","police within80m",true);
            add("tire-asphalt-drift","road tire loop",true);add("tire-gravel-drift","offroad tire loop",true);
            add("boot-asphalt-step","running recovery cadence",false);add("leather-road-slide","falling state entry",false);add("suspension-bottom","landing event",false);
            foreach(WeaponKind weapon in Enum.GetValues(typeof(WeaponKind))){add(Attack(weapon),"attack event sweep",false);add(Hit(weapon,0),"weapon contact event",false);add(Hit(weapon,1),"weapon contact variation",false);}
            add(Crash(350,false),"shoulder crash",false);add(Crash(500,false),"traffic/rider crash",false);add(Crash(700,true),"heavy crash or wreck",false);
            for(int character=0;character<reactions.Length;character++)for(int cue=0;cue<reactions[character].Length;cue++)add(reactions[character][cue],CharacterCatalog.GetAt(character).Id+" reaction slot "+cue,false);
            return roles.AsReadOnly();
        }
    }
}
