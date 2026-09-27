using System;
using System.Collections.Generic;
namespace RacingBois.Gameplay.Definitions
{
    public sealed class CharacterDefinition
    {
        public int CatalogIndex { get; }
        public string Id { get; }
        public string DisplayName { get; }
        public string ArtId => "RB_P08_Rider_" + CatalogIndex.ToString("D2");
        internal CharacterDefinition(int index, string id, string name) { CatalogIndex = index; Id = id; DisplayName = name; }
    }
    /// <summary>Cosmetics only. Identity never changes collision, health, strength or rewards.</summary>
    public static class CharacterCatalog
    {
        public const int Count = 8;
        public const string DefaultId = "rb-ash";
        private static readonly CharacterDefinition[] entries = {
            new CharacterDefinition(0,"rb-ash","Ash"), new CharacterDefinition(1,"rb-juno","Juno"),
            new CharacterDefinition(2,"rb-mako","Mako"), new CharacterDefinition(3,"rb-rook","Rook"),
            new CharacterDefinition(4,"rb-sol","Sol"), new CharacterDefinition(5,"rb-vale","Vale"),
            new CharacterDefinition(6,"rb-echo","Echo"), new CharacterDefinition(7,"rb-kai","Kai")
        };
        public static IReadOnlyList<CharacterDefinition> All { get; } = Array.AsReadOnly(entries);
        public static CharacterDefinition GetAt(int index)
        { if (index < 0 || index >= Count) throw new ArgumentOutOfRangeException(nameof(index)); return entries[index]; }
        public static bool TryGet(string id, out CharacterDefinition definition)
        { foreach (var entry in entries) if (string.Equals(entry.Id,id,StringComparison.Ordinal)) { definition=entry; return true; } definition=null; return false; }
    }
}
