# Contact-impulse derivative guard — applied, runtime review continuing

The first protocol6 stress run retained a false local crash after a soft pair collision. At authoritative tick1912, neighbors4/6 had collision protection until1922, snapshot acceleration estimates−18000mm/s² and lateral estimates±1400mm/s. Their next snapshot at1915 estimated positive acceleration instead. The physics applies a one-time1200mm/s speed reduction at a soft pair collision; interpreting a sample interval containing that impulse as continuous deceleration can create a later high-relative-speed collision that authority never produces.

The immutable [capture](../proxy-transition-staging/first-production-outlier.json) and [kinematics counterfactual](../proxy-transition-staging/first-production-kinematics.json) isolate this: setting only the two acceleration estimates to zero removes the false fall and matches every later-rebased checkpoint field. Changing lateral estimates alone does not. The raw correction is1.2126m and the recorded presented-pose change1.9305m. The immediately previous private interval snapshot was not retained, so the evidence is stated as an exact counterfactual plus independently authored metadata-boundary tests, not a fabricated full historical guard replay.

The candidate changes only three Application files:

- Retain the previous validated immutable `MultiplayerSnapshotReadModel` alongside its visual world; clear it on race/room reset.
- Pass complete current/previous snapshot objects to neighbor projection so the metadata stays tied to its own tick.
- Skip deriving acceleration/lateral/vertical velocity from a sample interval when current collision protection is **active** and its absolute expiry has advanced. Preserve the current authoritative position/speed. Expired protection clamped to `currentTick` is not a new grant. Unchanged protection and genuine braking continue to use the existing estimator. Missing history produces zero estimates rather than inventing data.

No protocol, server, simulation, timing, horizon, authority damage or economy source changes are included. The original low-level validated projection overload remains for metadata tests; production calls the complete immutable snapshot overload.

[Candidate tests](candidate.json) pass11groups: positive impulse case, genuine braking, unchanged immunity, expiry-clamp boundaries, first observation/missing history, immutable ownership, reset lifecycle, unchanged0/150/250ms gates and exact recorded counterfactual. [Full isolated regression](full-regression-20260926T232602Z/receipt.json) passes252groups in16suites with stable source. The candidate manifest SHA256 is `f6f2e6e05b85cee741eec91090aefc6c069abf75ef543c79013b807cbfc431ea`.

Root reviewed and applied the complete7-file manifest after the30-minute run completed and Unity returned idle. [Applied bindings](applied-source-freeze.json) match that manifest. [Fresh production regression](../regression/20260926T233520Z/receipt.json) passes252groups with stable source; fresh90-second network smoke `20260926T233717Z` is a separate pending receipt. No8-hour acceptance has been claimed. Backend f runtime remains protocol6 and is independently compatible; its immutable packaged ARM client-test source predates this client-only guard, so those148ARM groups do not claim to cover the new guard. The current Windows/.NET252-group receipt covers it.

The separate police episode at665.785seconds is not covered: local6 predicted Wrecked while authority stayed Riding, with no new protection interval and a police acceleration estimate changing−600→+12400. It remains explicitly recorded for bounded presentation/native review. This candidate does not guess future AI decisions or claim to eliminate every correction.
