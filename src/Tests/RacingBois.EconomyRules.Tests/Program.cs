using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text.Json;
using RacingBois.Gameplay.Definitions;

var results = new List<object>();
int failures = 0;
void Test(string name, Action action)
{
    try { action(); results.Add(new { name, passed = true }); Console.WriteLine("PASS " + name); }
    catch (Exception error) { failures++; results.Add(new { name, passed = false, error = error.Message }); Console.WriteLine("FAIL " + name + ": " + error.Message); }
}
void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
void Throws<T>(Action action) where T : Exception
{
    try { action(); }
    catch (T) { return; }
    throw new InvalidOperationException("Expected " + typeof(T).Name);
}

Test("reference_price_trade_and_repair_tables_match_all_15_extracted_rows", () =>
{
    using var reference = JsonDocument.Parse(File.ReadAllText("docs/reverse-engineering/logic/economy_tables.json"));
    var rows = reference.RootElement.GetProperty("bikes");
    Check(rows.GetArrayLength() == BikeCatalog.Count, "Catalog lost a reference SKU.");
    foreach (var row in rows.EnumerateArray())
    {
        var bike = BikeCatalog.GetAt(row.GetProperty("internal_index").GetInt32());
        Check(bike.PriceCredits == row.GetProperty("price").GetInt32(), "Price mismatch for " + bike.Id);
        Check(bike.TradeInCredits == row.GetProperty("trade_in").GetInt32(), "Trade mismatch for " + bike.Id);
        Check(bike.RepairCredits == row.GetProperty("repair").GetInt32(), "Repair mismatch for " + bike.Id);
        Check(bike.DisplayName != row.GetProperty("name").GetString(), "Reference product name leaked into new catalog.");
    }
});

Test("stable_unique_case_sensitive_ids_and_unknown_ids_do_not_fall_back", () =>
{
    var ids = new HashSet<string>(StringComparer.Ordinal);
    foreach (var bike in BikeCatalog.All)
    {
        Check(ids.Add(bike.Id), "Duplicate bike ID.");
        Check(ReferenceEquals(BikeCatalog.GetAt(bike.CatalogIndex), BikeCatalog.Get(bike.Id)), "Lookup mismatch.");
        Check(!BikeCatalog.TryGet(bike.Id.ToUpperInvariant(), out _), "Case-folding changed ID contract.");
    }
    Check(!BikeCatalog.TryGet(null, out _) && !BikeCatalog.TryGet("../rb-spark-450", out _), "Invalid ID accepted.");
    Throws<ArgumentException>(() => BikeCatalog.Get("not-a-bike"));
    Throws<ArgumentOutOfRangeException>(() => BikeCatalog.GetAt(-1));
    Throws<ArgumentOutOfRangeException>(() => BikeCatalog.GetAt(15));
});

Test("catalog_collections_cannot_be_mutated_through_collection_interfaces", () =>
{
    var bikes = (IList<BikeDefinition>)BikeCatalog.All;
    Throws<NotSupportedException>(() => bikes[0] = bikes[1]);
    Throws<NotSupportedException>(() => bikes.Clear());
    var routes = (IList<CampaignRouteDefinition>)CampaignCatalog.Routes;
    Throws<NotSupportedException>(() => routes.RemoveAt(0));
});

Test("p08_catalog_maps_stable_prices_to_authored_handling_and_art_gate", () =>
{
    int distinctArt = 0;
    foreach (var bike in BikeCatalog.All)
    {
        if (bike.HasDistinctArt) distinctArt++;
        Check(bike.ArtId == "RB_P08_Bike_" + bike.CatalogIndex.ToString("D2"), "Wrong production model identity.");
        Check(bike.Handling.CatalogIndex == bike.CatalogIndex, "Handling profile mapping mismatch.");
        Check(bike.MaximumSpeedMillimetersPerSecond >= 47000 && bike.MaximumSpeedMillimetersPerSecond <= 79000, "Invalid P08 speed cap.");
    }
    Check(distinctArt == System.Numerics.BitOperations.PopCount((uint)ProductionContent.AvailableBikeArtMask) && BikeCatalog.Get(BikeCatalog.StarterBikeId).CatalogIndex == 0, "Starter art contract changed.");
    Check(EconomyRules.StartingCredits == 1000, "New-profile choice changed without migration/review.");
});

Test("integer_quotes_round_down_and_handle_maximum_valid_int", () =>
{
    Check(EconomyRules.TradeInValue(4495) == 2247, "Odd trade rounding.");
    Check(EconomyRules.RepairCost(4495) == 449, "Odd repair rounding.");
    Check(EconomyRules.TradeInValue(int.MaxValue) == 1073741823, "Trade overflow.");
    Check(EconomyRules.RepairCost(int.MaxValue) == 214748364, "Repair overflow.");
    Check(EconomyRules.TradeInValue(0) == 0 && EconomyRules.RepairCost(0) == 0, "Zero quote.");
    Throws<ArgumentOutOfRangeException>(() => EconomyRules.TradeInValue(-1));
    Throws<ArgumentOutOfRangeException>(() => EconomyRules.RepairCost(int.MinValue));
});

Test("reference_reward_schedule_matches_all_70_level_position_combinations", () =>
{
    using var reference = JsonDocument.Parse(File.ReadAllText("docs/reverse-engineering/logic/economy_tables.json"));
    var expected = reference.RootElement.GetProperty("reward_base_by_position");
    for (int level = 0; level < 5; level++)
    {
        Check(EconomyRules.BustFine(level) == new[] { 400, 800, 1200, 1600, 2000 }[level], "Fine mismatch.");
        for (int rank = 1; rank <= 14; rank++)
            Check(EconomyRules.RewardForRank(rank, level) == expected[rank - 1].GetInt32() * (level + 1), "Prize mismatch.");
        Check(EconomyRules.RewardForRank(15, level) == 0 && EconomyRules.RewardForRank(16, level) == 0, "Extra rider received invented reference prize.");
    }
});

Test("invalid_reward_inputs_fail_instead_of_clamping_to_a_payable_result", () =>
{
    Throws<ArgumentOutOfRangeException>(() => EconomyRules.RewardForRank(0, 0));
    Throws<ArgumentOutOfRangeException>(() => EconomyRules.RewardForRank(17, 0));
    Throws<ArgumentOutOfRangeException>(() => EconomyRules.RewardForRank(1, -1));
    Throws<ArgumentOutOfRangeException>(() => EconomyRules.RewardForRank(1, 5));
    Throws<ArgumentOutOfRangeException>(() => EconomyRules.BustFine(-1));
    Throws<ArgumentOutOfRangeException>(() => EconomyRules.BustFine(5));
});

Test("logical_25_slot_campaign_advances_only_after_five_distinct_qualified_courses", () =>
{
    int level = 0, mask = 0;
    bool completed = false;
    int completedSlots = 0;
    for (int stage = 0; stage < 5; stage++)
        foreach (int course in new[] { 4, 2, 0, 3, 1 })
        {
            var next = CampaignRules.ApplyQualification(level, mask, completed, course, 3);
            completedSlots++;
            if (course != 1)
            {
                Check(next.LevelIndex == stage && !next.Completed, "Advanced before all course bits qualified.");
                var repeat = CampaignRules.ApplyQualification(next.LevelIndex, next.QualificationMask, next.Completed, course, 1);
                Check(repeat.LevelIndex == next.LevelIndex && repeat.QualificationMask == next.QualificationMask, "Repeated course progressed twice.");
            }
            else if (stage < 4) Check(next.LevelIndex == stage + 1 && next.QualificationMask == 0, "Level rollover not atomic.");
            level = next.LevelIndex; mask = next.QualificationMask; completed = next.Completed;
        }
    Check(completedSlots == 25 && completed && level == 4 && mask == 31, "Final campaign state mismatch.");
    var after = CampaignRules.ApplyQualification(level, mask, completed, 0, 1);
    Check(after.Completed && after.LevelIndex == 4 && after.QualificationMask == 31, "Completed campaign advanced again.");
});

Test("qualification_top_three_boundary_is_independent_of_prize_eligibility", () =>
{
    for (int rank = 1; rank <= 16; rank++)
    {
        var state = CampaignRules.ApplyQualification(0, 0, false, 2, rank);
        Check(state.QualificationMask == (rank <= 3 ? 4 : 0), "Incorrect qualification rank " + rank);
    }
    Check(EconomyRules.RewardForRank(4, 0) == 400, "Nonqualified finish incorrectly has no prize.");
});

Test("invalid_or_unsettled_progress_is_rejected_without_mask_normalization", () =>
{
    foreach (int mask in new[] { -1, 32, 63, int.MaxValue })
        Throws<ArgumentOutOfRangeException>(() => CampaignRules.ValidateProgress(0, mask, false));
    Throws<ArgumentException>(() => CampaignRules.ValidateProgress(0, 31, false));
    Throws<ArgumentException>(() => CampaignRules.ValidateProgress(4, 31, false));
    Throws<ArgumentException>(() => CampaignRules.ValidateProgress(4, 30, true));
    Throws<ArgumentException>(() => CampaignRules.ValidateProgress(0, 0, true));
    Throws<ArgumentOutOfRangeException>(() => CampaignRules.ApplyQualification(0, 0, false, -1, 1));
    Throws<ArgumentOutOfRangeException>(() => CampaignRules.ApplyQualification(0, 0, false, 5, 1));
    Throws<ArgumentOutOfRangeException>(() => CampaignRules.ApplyQualification(0, 0, false, 0, 0));
});

Test("authored_routes_require_matching_production_availability_gate", () =>
{
    Check(CampaignCatalog.Routes.Count == 5 && CampaignCatalog.LevelCount == 5, "Campaign definition incomplete.");
    var ids = new HashSet<string>(StringComparer.Ordinal);
    foreach (var route in CampaignCatalog.Routes)
    {
        Check(ids.Add(route.Id), "Duplicate route ID.");
        Check(CampaignCatalog.TryGetRoute(route.Id, out var found) && ReferenceEquals(found, route), "Route lookup mismatch.");
        Check(route.IsPlayable == ProductionContent.RouteAvailable(route.CourseIndex), "Unauthored route playable.");
        Check(route.ContentId.Length > 0, "Missing playable-content identity or fake unproduced content identity.");
    }
    Check(!CampaignCatalog.IsPlayableRoute(-1) && !CampaignCatalog.IsPlayableRoute(5), "Out-of-range route accepted.");
    Check(!CampaignCatalog.TryGetRoute(null, out _), "Null route accepted.");
});

string output = args.Length > 0 ? args[0] : "docs/p07/economy-rules-validation.json";
var sourceFiles = new List<object>();
foreach (string path in new[]
{
    "Packages/com.racingbois.foundation/Runtime/Definitions/BikeCatalog.cs",
    "Packages/com.racingbois.foundation/Runtime/Definitions/EconomyRules.cs",
    "Packages/com.racingbois.foundation/Runtime/Definitions/CampaignCatalog.cs",
    "Packages/com.racingbois.foundation/Runtime/Definitions/CampaignRules.cs",
    "Packages/com.racingbois.foundation/Runtime/Definitions/GameplayRules.cs",
    "docs/reverse-engineering/logic/economy_tables.json",
    "src/Tests/RacingBois.EconomyRules.Tests/Program.cs"
})
    sourceFiles.Add(new { path, sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() });
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output, JsonSerializer.Serialize(new
{
    generatedAtUtc = DateTimeOffset.UtcNow,
    passed = failures == 0,
    tests = results.Count,
    failures,
    scope = "Pure shared catalog/quote/campaign rules only; not database transaction, Unity/browser, or original full-campaign runtime proof.",
    runtime = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription,
    sourceFiles,
    results
}, new JsonSerializerOptions { WriteIndented = true }));
return failures == 0 ? 0 : 1;
