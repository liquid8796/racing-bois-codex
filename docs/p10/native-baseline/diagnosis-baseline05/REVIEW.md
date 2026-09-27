# Independent review of native baseline05

The original run is preserved as a **verified recording with failed foreground
coverage**. Separate standard-library CSV recomputation found562,640 contiguous
Unity frame indices,600.1540975seconds, no interval/tick-step violations,36,000
measured simulation ticks and ten observed world restarts. Raw timings match the
native summary:937.4926Unity-loopFPS, p95 1.7294ms and maximum154.3898ms.

Only108.9235359seconds were focused (18.1493%). Focus first left at80.1275seconds;
later brief foreground periods do not meet the declared99% window condition.
All samples remain present, including background intervals. API, resolution,
quality and timing policy stayed Direct3D11,1920x1080,Medium,uncapped/noVSync.

Win32 memory sampling succeeded600times with no read errors. Working set ranged
444,354,560–469,377,024bytes, while private committed bytes ranged
848,945,152–874,651,648bytes. Sampling covered the window from0.0001305seconds to
599.348054seconds. These are sampled process values; graphics-driver
allocation and dedicated GPU residency are unavailable. This corrects native04's
unusable zero-valued managed Process counters without modifying that earlier run.

All562,640 native timing timestamps were distinct. GPU timing was available for
475,849 rows: median0.623616ms, p95 1.189888ms, maximum22.32832ms. None exceeded the
whole observation window, unlike the two retained anomalies in04. No GPU values
were removed to improve the result. Available workload render counters supplied
562,639 set-pass/triangle/vertex observations, with nonzero means but zero minima.
Draw-call and batch counters remained unavailable. This supports sustained native
rendering activity, not physical display refresh or a guarantee that every loop
iteration presented a visible frame.

The launcher recorded unchanged source/player bytes before and after execution,
exit0 and stopped ownership. The copied native build receipt independently
records successful source binding, settings restoration and font preservation.
Original user font bytes remain protected and outside commits.

[Recomputation and focus segments](independent-review.json) binds the original
launch, raw frames, memory and runtime receipt by SHA256. `measurementPassed`,
`p08Accepted` and `releaseAccepted` remain false. Normal game UI/network/input,
production P08 art, the hardware matrix and foreground qualification remain open.
