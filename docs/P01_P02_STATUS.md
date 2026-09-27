# Racing Bois — P01 / P02

Đây là hồ sơ triển khai sau yêu cầu thực hiện P01 và P02. P00 giữ nguyên như một snapshot lịch sử.

## P01 — Kết quả đã có

- [Logic và native runtime](p01/logic/LOGIC_P01.md): project phân tích lưu được, component fixtures trên mã x86 gốc, EXE bản sao chạy windowed với trace thực.
- [Native combat và AI](p01/logic/NATIVE_CONTACTS_AND_AI.md): damage, cooldown, transfer, cop/traffic và Busted có bằng chứng; 6.075 component fixtures.
- [Assets/course/media](p01/assets/REPORT.md): 5 course, 141 node, 109 segment, 34.182 samples, atlas và metadata animation, course→163 FAM reference ledger.
- [RPTH/legacy closure](p01/assets/FOLLOWUP_CLOSURE.md): 171.466 native path checks; phân loại các legacy records thay vì giả giải mã.
- [HUD units/course lengths](p01/assets/DISPLAY_UNITS.md): 1.086 fixtures, 25 length values, speed/distance conversion có địa chỉ.

**Không đánh dấu P01 đạt 100% logic.** Vẫn còn các nhánh AI/relationship/avoidance và natural spawning; collision/slope/airborne coverage đầy đủ; animation anchors/hit windows; media/menu/campaign/economy transitions đầy đủ và đối chiếu vanilla. Các báo cáo chứa gate riêng để tiếp tục, không suy phần trăm từ số tests/instructions.

## P02 — Foundation đã chạy và kiểm chứng

- Unity WebGL2 + URP 17.5.0 + Input System 1.20.0; Editor 6000.5.7f1, Unity MCP pin commit.
- Shared C# definitions/simulation/protocol tách khỏi Unity; .NET 10 authority 60 Hz / snapshots20 Hz, giới hạn8 players, validation và queues hữu hạn.
- [Backend tests và transport](p02/backend/README.md): 18 nhóm tests, immutable readmodel boundary, 8 synthetic peers, stream stall/flood và WSS certificate controls.
- [Unity browser validation](p02/BROWSER_VALIDATION.md): real Web build, WS/WSS, hai browser clients, fixture dùng chung và input thật.
- [Blender QA](p02/assetqa/REPORT.md): barrier mới hoàn toàn, `.blend`, FBX, 3 LOD252/126/50, maps và UV; Unity prefab có BoxCollider, LODGroup, URP, UV2 và root chuẩn.
- OCI target do người dùng cung cấp đã được preflight: ARM64,4 logical CPUs, khoảng23.4 GiB RAM; self-contained native smoke PASS. Không triển khai service công khai hoặc thay đổi Caddy/database hiện có.
- Git và tooling build/test/publish/research đã được tạo. Source game cuối ở commit `906593098208af8ba80e48e002ec34aa08ca33f8`; build từ thư mục xuất Git độc lập, không dùng Library project chính, đã PASS 0 errors/0 warnings. Lần build cold đầu gặp giới hạn nội bộ Bee; một lần chạy lại hoàn tất, wrapper có kiểm tra retry hữu hạn và không che lỗi khác.
- Gói cuối: `Build/Web-9065930-r2`, `Build/LanHost/win-x64-9065930`, `Build/LanHost/linux-arm64-9065930`; assets Web có đủ trong gói, không chứa `_DoNotShip`. Native ARM64 đã chạy trên VM chỉ định rồi dọn thư mục tạm.

[Build receipt](p02/unity/final-build.json), [kiểm tra wrapper](p02/unity/build-wrapper-tests.json), [view lifecycle](p02/unity/view-lifecycle.json), [publish hashes](p02/backend/publish-evidence.json), [ARM64 smoke](p02/oci/arm64-smoke.json).

Đây là prototype foundation. Cảm giác lái Road Rash hoàn chỉnh, combat/AI production, campaign, account/database, art đầy đủ và Internet/LAN nhiều máy thuộc các phase sau. Foundation dùng rules thử nghiệm có version; không gọi chúng là logic gốc đã port.
