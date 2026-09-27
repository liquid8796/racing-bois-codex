# P08 — Independent technical art review, 2026-09-26

## Kết luận

**Chưa đủ điều kiện chốt các asset P08 là production-ready cho Windows 10/11.** Có công việc kỹ thuật thật và nhiều phần có thể giữ lại: geometry/FBX tự tạo, material URP, LOD, pivot, primitive collider và bộ rig/animation P06. Tuy nhiên evidence P08 hiện chưa theo kịp file thực tế; UV/material chỉ vượt kiểm tra cấu trúc, chưa đạt bằng chứng chất lượng ở góc nhìn gần; roster nhân vật còn chưa xuất thành công. Không nên xóa hàng loạt nguồn hoặc nghiệm thu chỉ dựa trên các giá trị `passed: true` cũ.

Review này chỉ đọc file, receipt, code và metadata. Có thêm parser FBX độc lập để đo UV từ bytes export hiện tại; không mở/sửa scene Blender, không chạy Unity import và không sửa production assets. Phần đánh giá hình dáng, phong cách và độ trung thành concept cần đọc cùng review hình ảnh của nhóm.

Nguồn tiêu chuẩn: `docs/REQUIREMENTS.md`, mục 3–5 và bổ sung Windows/UI ngày 2026-09-26. Các số liệu bên dưới là snapshot hiện tại, không phải phần trăm hoàn thành game.

## Tồn kho và độ tin cậy evidence

| Nhóm | File hiện có / kiểm chứng | Giới hạn |
|---|---|---|
| P08 manifest | 36 semantic exports: 12 bikes (01–12), 18 scenery, 2 landmarks, 4 foliage | `passed: false`, trạng thái awaiting QA; chưa có Bike13/14 hoặc rider production |
| P08 FBX | 36 FBX, 60 meshes LOD0; parser độc lập đọc 355,022 triangles LOD0 | Tổng inventory, không phải lượng render đồng thời |
| P08 prefabs | 30 prefab files, gồm Bike00 alias | Chỉ 29 IDs có Unity receipt cũ; alias tái dùng Spark P06 không tăng số thiết kế mới |
| P08 Unity receipt | 29 IDs, Unity 6000.5.7f1; file từ 2026-09-22 | Thiếu Bike06–12; Bike01–05 trong receipt là phiên bản geometry cũ |
| P08 source receipt | `source-audit-summary.json` ghi PASS, 36 exports / 180 meshes | 6 Ridge assets hiện không khớp source/FBX hashes trong manifest; không thể dùng PASS này cho bytes hiện tại |
| P08 riders / portraits | 0 rider FBX, 0 portraits PNG hoàn thiện | `rider-00-creation-mcp.json` chứa lỗi Blender context; recipe mới không phải sản phẩm đã xuất |
| P06 hero reuse | 5 geometry exports / 6 prefab variants; 125/125 file hashes khớp manifest | Evidence kỹ thuật cũ còn khớp bytes; chưa thay cho nghiệm thu desktop mới |
| P06 environment reuse | 75/75 file hashes khớp manifest | Cũng cần review hình ảnh/performance theo target desktop |
| P04 club | 24/25 file hashes khớp manifest cũ | `.blend` là thay đổi có sẵn của người dùng, phải giữ nguyên; không tự re-export hoặc ghi đè |

Snapshot đọc file: [technical-current-snapshot.json](technical-current-snapshot.json). Kết quả UV có SHA-256 từng FBX: [fbx-uv-readonly.json](fbx-uv-readonly.json). Công cụ đọc không ghi asset: [inspect_fbx_uv_readonly.py](inspect_fbx_uv_readonly.py).

Club được kiểm tra trong lần review này và vẫn đúng SHA-256 được yêu cầu bảo toàn: `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`.

## Findings cần xử lý trước khi tiếp tục sản xuất hàng loạt

### P1 — Evidence chưa ràng buộc đầy đủ với phiên bản asset thực tế

- `Assets/RacingBois/Art/P08/ArtManifest.json:991` vẫn ghi RidgeFir LOD0 **4,202** triangles; FBX hiện tại đo được **10,476**. Cả sáu Ridge assets có source/FBX hash mismatch. Bộ `.blend` chung làm hash nguồn của cả nhóm đổi khi một phần trong scene được chỉnh; FBX của cả sáu cũng đã đổi.
- Bike01 trong `docs/p08/art/unity-validation.json` ghi **15,704 / 6,898 / 2,394**, trong khi manifest và FBX hiện tại là **21,752 / 9,496 / 3,216**. Tương tự cả Bike02–05. Như vậy receipt Unity đang xác nhận một revision khác.
- `tools/p08/art/finalize.py:19–31` kiểm tra danh sách tên trong audit/Unity receipt, rồi so current bytes với manifest. Audit nguồn không mang hash nguồn tại thời điểm chạy; Unity receipt không mang hash FBX, importer, maps, builder hoặc dependency. Sau khi `collect.py:20–24` ghi lại hash mới, một receipt cũ có cùng tên asset có thể không bị phát hiện. Việc hash receipt trong manifest cuối chỉ chứng minh receipt là file nào, không chứng minh nó đã kiểm tra bytes asset nào.

**Gate:** freeze asset revision; record input hash trước/sau audit; chỉ dùng receipt nếu hash concept/source/FBX/maps/importer/prefab/rig/shared clips khớp. Rerun source audit và Unity import/validation cho chính revision đó. Giữ receipt cũ làm lịch sử, không đổi nhãn thành nghiệm thu mới.

### P1 — UV/texture hiện đạt điều kiện có channel và không overlap cục bộ, chưa chứng minh mật độ/detail dùng được

- `tools/p06/hero/common.py:13–49` sinh atlas 4×4 gồm các ô màu/material và micrograin; `finish():62–64` smart-project mỗi primitive vào tile. `export():128–157` unwrap lại toàn bộ mesh cuối, co UV vào tile và đẩy triangle cần sửa sang một dải rất hẹp. P08 kế thừa toàn bộ helper qua `tools/p08/art/compose.py:16–20`.
- Atlas P08 thật đã đọc/xem: BaseColor **1024²**; Normal/MetallicSmoothness/Roughness **512²**. Một ô material chỉ có tối đa **256² / 128²**, rồi còn padding và phần diện tích thực được UV sử dụng. Atlas có material variation cấp nhỏ; không có texture đặc thù theo vùng của vỏ xe, đường may, biển hiệu hay landmark ngoài geometry/ô màu. Đây có thể là lựa chọn có chủ ý cho phong cách đơn giản, nhưng không tự đáp ứng concept nhiều chi tiết hoặc camera garage/cutscene gần.
- `tools/p06/hero/audit.py:37–53` chỉ kiểm tra UV ngoài 0–1, diện tích không-zero và triangle intersection trong từng connected component. Nó không đo texels/meter, tỷ lệ stretch, padding ở mip cần dùng, continuity/texel alignment, chất lượng compression hoặc hình ảnh sau normal mapping. Overlap giữa component/LOD được khai báo intentional, vì vậy không gọi các overlap này là lỗi mặc định.

Parser độc lập trên FBX hiện tại cho thấy lý do cần gate mạnh hơn:

| Mesh LOD0 | Triangles | Triangles có UV area < 1 texel tại BaseColor 1024² | Median UV area (texel²) |
|---|---:|---:|---:|
| Bike01 Body | 10,000 | 9,034 | 0.0431 |
| Bike05 Body | 10,000 | 9,308 | 0.0262 |
| CoastPalm | 6,704 | 6,567 | 0.1235 |
| RidgeFir hiện tại | 10,476 | 10,470 | 0.0263 |
| CityWarehouse | 8,572 | 8,119 | 0.000448 |

**Không được suy từ bảng này rằng mọi triangle nhỏ là lỗi.** Nhiều bevel/details nhỏ có thể dùng màu phẳng hợp lệ; CityWarehouse có nhiều bevel nhỏ trong khi diện tích mặt lớn vẫn có UV lớn. Ngược lại, với RidgeFir hầu hết diện tích hình học cũng rơi vào các triangle có UV subpixel, nên atlas microdetail khó tạo ra chi tiết foliage hữu ích. Đây là bằng chứng cần quyết định rõ giữa phong cách hình khối/màu phẳng và vật liệu có detail; không thể quảng cáo chỉ từ việc file Normal tồn tại.

**Gate:** chọn một xe và một môi trường làm mẫu chất lượng; đo texel density theo camera gần/đua, inspect UV checker/material mip ở 1080p; sử dụng UV islands/trim/tile/decal phù hợp bề mặt. Chỉ tăng resolution khi chứng minh UV đang sử dụng có ích, không chỉ upscale bản atlas cũ. Giữ reuse tile khi phù hợp, nhưng khai báo theo bề mặt cụ thể.

### P1 — Rider/portrait mới chưa tồn tại; recipe còn chưa đủ bằng chứng deformation và chất lượng khuôn mặt

- `docs/p08/art/rider-00-creation-mcp.json:69` ghi `bpy.ops.object.mode_set.poll() Context missing active object`. Wrapper `isError: false` không biến lỗi bên trong thành export thành công. Không có successful batch report hoặc rider FBX/portrait PNG để review. `collect.py` có kiểm tra marker thành công, nên không nên thêm receipt lỗi này vào inventory thành công.
- `tools/p08/art/riders.py:5–10` mới có bốn identity definitions. Các phần mô tả eight identities/24 portraits ở cuối `docs/p08/art/README.md` đang mô tả mục tiêu/recipe, không phản ánh output hiện tại.
- Recipe tạo mặt từ các volume rời và shape keys theo vùng tọa độ (`riders.py:79–95, 131–143`). Kiểm tra `P08ArtBuilder.cs:175–183` chỉ yêu cầu Happy/Focused tồn tại và có delta khác zero; chưa chứng minh expression trông đúng, topology mặt không tách hoặc mắt/mũ bảo hiểm không xuyên nhau.
- P08 sampler kiểm tra finite vertices/bounds và rotation khác bind pose (`P08ArtBuilder.cs:190–239`). Điều đó không chứng minh chuyển động liên tục, loop khép, tay chạm grip đúng trên từng xe, chân không xuyên xe hoặc garments không xuyên cơ thể. Bộ P06 hiện có kiểm tra temporal rotation và 17 phase/clip, nhưng reuse rig không đảm bảo mọi mesh nhân vật mới biến dạng tốt.

**Gate:** làm xong một nhân vật mẫu trước khi nhân rộng. Review neutral + expressions ở portrait512, garage và gameplay; sau đó thử cả12 clip, loop endpoints, transition, weapon attachment, chạy/ngã/lên xe; đối chiếu hand/seat/foot contacts với các hình dáng xe. Chỉ tạo24portrait cuối từ model đã chốt.

### P2 — Standalone compression mới nằm trong code, chưa được áp dụng vào metadata hiện tại

- `P08ArtBuilder.cs:72–73` yêu cầu Standalone BC7 cho colour/mask, BC5 cho normal. Nhưng ví dụ `Assets/RacingBois/Art/P08/RB_P08_BikesA_Atlas_Normal.png.meta:84–92` hiện có `textureFormat: -1`, `overridden: 0`; các atlas BaseColor P08 được kiểm tra cũng vậy. Không đủ căn cứ nói bản hiện tại đã dùng BC7/BC5.
- P06 hero và Club importer chỉ đặt override WebGL (`P06HeroAssetBuilder.cs:51–55`, `ClubAssetBuilder.cs:33–37`). Automatic Standalone có thể là cấu hình hợp lệ; cần đọc format đã import/build và chất lượng thực, không mặc định xem nó là hỏng.

**Gate:** sau khi chốt source, chạy import đúng Windows target, kiểm tra actual format/sRGB/normal channel/mask alpha/mip/texture memory ở player. Xác nhận lại material packing: metallic ở R, smoothness = 1−roughness ở A, scalar smoothness1. Contract này trong recipe/material hiện là hợp lý (`common.py:34–39`, `P08ArtBuilder.cs:85–91`).

### P2 — LOD và mesh budget kiểm tra còn quá yếu để kết luận hiệu năng

- Current bikes LOD0 nằm trong **21,152–22,336** triangles, 3 renderers/LOD; LOD1 khoảng9k, LOD2 khoảng3k. Đây không tự là budget quá lớn cho PC, nhưng cần số actor đồng thời, shadow passes, visible scenery và frame cost thực.
- `P08ArtBuilder.cs:129–136` dùng chung screen thresholds **.22 / .075 / .009**, không crossfade. `Validate():269` chỉ yêu cầu triangle count giảm; không kiểm tra silhouette popping, số draw calls, skinning cost, shader cost hoặc mức tăng geometry như RidgeFir.
- `P08ArtBuilder.cs:103` bật `isReadable = true` cho mọi P08 model, kể cả scenery tĩnh. CPU mesh copy có thể cần cho một số bước QA, nhưng runtime need chưa được chứng minh. Không nên gọi memory optimized khi chưa đo và chưa tắt read/write với meshes không cần đọc sau build.
- BaseColor1024/Normal512 và một material là cấu hình tiết kiệm; ngược lại quá ít texture detail để bù geometry có thể dẫn đến hình khối nhiều polygon nhưng vẫn phẳng. Số lượng material/LOD hợp lệ không thay cho cân bằng hình ảnh/chi phí.

**Gate:** đánh giá chuyển LOD khi chạy nhanh và nhìn gần, shadow silhouette, tổng triangle/draw/VRAM/CPU memory ở scene thật; đo trên native Windows player bằng cùng camera/workload trước–sau. Chỉ ghi PASS performance khi có hardware, resolution, quality preset, thời lượng và profiler evidence cụ thể.

### P2 — Collider/pivot pass chưa xác nhận gameplay collision khớp hình ảnh

- P08 tạo một BoxCollider theo toàn bộ bounds hoặc capsule cho pole/rider (`P08ArtBuilder.cs:137–156`) và chỉ kiểm tra loại/số lượng collider (`:270–271`). Điều này tốt hơn MeshCollider không cần thiết, nhưng chưa đo độ khớp với authority proxy.
- Runtime cố ý disable các collider actor (`RaceStageView.cs:116–127`) và Club (`WeaponGripView.cs:39`); core simulation quyết định va chạm. Vì vậy “prefab có collider” không phải bằng chứng chống xuyên/đánh trúng chính xác trong game.
- P06 traffic validator có kiểm tra envelope/collider dimensions (`P06HeroAssetBuilder.cs:360–364`). Cần giữ gate này cho traffic mới và thêm việc so visually selected bike/rider với authority envelope, hand/weapon sockets và wheel pivots.

**Gate:** overlay debug server proxy trong scene gameplay; kiểm tra tường/xe/đòn đánh ở hai bên, khi nghiêng xe và khi ngã. Với landmark có lối đi, giữ khoảng rỗng; không tạo box chặn cả lối chỉ để đạt count1.

## Những phần kỹ thuật nên giữ

- Bộ authoring tự tạo, nguyên tắc concept → Blender → FBX → prefab, semantic IDs và việc không cộng LOD/alias thành nhiều thiết kế.
- URP Lit shared material, packing metallic/smoothness đúng chiều; texture non-colour được phân loại rõ trong recipe/importer.
- Ba LOD và wheel pivots riêng; meters/identity prefab roots; normals/tangents có channel; geometry audit manifold/volume/UV là nền hữu ích.
- Generic15bone P06,12clip gốc và root motion off; GPU skinning Bone2 phù hợp trọng số tối đa2 được khai báo. Chưa cần đổi rig chỉ vì target chuyển từ Web sang Windows.
- Dynamic lighting không cần UV2; source/importer không bật ContributeGI. Nếu chuyển sang baked lighting sau này mới yêu cầu UV2/padding/lightmap bake gate.
- Giữ Club và toàn bộ source P06 đã có hash evidence; review hình ảnh có thể yêu cầu polish hoặc remake phần hiển thị, nhưng không có lý do kỹ thuật để xóa các file đang có trước khi replacement được kiểm chứng.

## Thứ tự xử lý được khuyến nghị

1. Giữ snapshot hiện tại và đánh dấu rõ pending/rejected/accepted theo từng semantic asset; chưa xóa production dependency.
2. Chốt **một xe + một rider + một nhóm môi trường** ở mức hình ảnh desktop cần đạt, có concept phù hợp, UV/material và nguồn Blender thật. Nếu mẫu không đạt thì thay quy trình authoring, không nhân rộng công thức hiện tại.
3. Chạy technical gates trên golden samples: source/FBX hashes, UV/material/LOD, real animation, collision overlay, Unity console, native player capture và profiler.
4. Chỉ sau đó remake/polish hàng loạt theo quyết định visual review. Thay GUID/reference có kiểm soát, giữ gameplay IDs và preserve user-owned Club source.
5. Rebuild exact Windows content/player từ revision freeze; receipt mới phải ràng buộc source/import/build hashes và phản ánh đủ roster thực. Content parity ledger chỉ promote khi từng nội dung qua gate, không từ số file hoặc compile success.

Không có xóa, re-export, regeneration hoặc chỉnh production code nào được thực hiện trong review này.
