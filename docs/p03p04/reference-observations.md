# P03/P04 — Quan sát các đoạn video gốc

Ngày2026-09-21. Chỉ phân tích file người dùng cung cấp, local-only bằng skill `watch` với `--no-whisper`; không upload media/audio và không đưa hình/âm thanh gốc vào production assets. Nguồn có SHA-256 `a270cca1f0a9866b43ca629fe0df1facd0a64bbb3ccb25f557c812ec8407554a`, phù hợp hồ sơ [GAMEPLAY_REFERENCE](../reverse-engineering/video/GAMEPLAY_REFERENCE.md).

Tái lập từ projectroot:

```powershell
python tools/p03p04/prepare_reference_clips.py
```

Output research-only/gitignored nằm tại `docs/p03p04/reference/`:

- `original-recovery-30m58s.mp4`: nguồn30:58,0–31:12,0,14giây.
- `original-combat-34m55s.mp4`: nguồn34:55,0–35:10,0,15giây.
- Mỗi clip có subfolder chứa cueframes640×480, contact sheets, watch report và frames.json ánh xạ chính xác clip-time→source-time.
- `reference-manifest.json` ghi SHA nguồn/clips, ffprobe metadata, exact ffmpeg/watch arguments. Các clip transcode H.264/AAC để xem được tiện; không sửa file nguồn.

Đã nhìn toàn bộ58frame lấy cách0,5giây trong4contactsheet. Không nghe/đánh giá audio; không có transcript. Nhãn `transcript-cue` của watch ở đây chỉ là tên loại forced timestamp, không có lời nói làm nguồn.

| Thời gian nguồn | Quan sát trực tiếp |
|---|---|
| 30:59,5 | Player còn ở trên xe, đi về phía phải đường. |
| 31:00,0 | Rider và bike tách rõ; rider bay phía trên bike ngã. Không xác định chắc trigger va chạm từ mẫu0,5s. |
| 31:00,5–31:02,5 | Rider và bike tumble/slide tách nhau; cuối chuỗi rider nằm trên đường. |
| 31:03,0–31:04,5 | Rider chuyển từ nằm/cúi sang đứng. Không đo được tick animation từ mẫu này. |
| 31:05,0–31:06,5 | Rider chạy về bike ở phía trước; đối thủ/traffic tiếp tục đi. |
| 31:07,0 | Rider đang cúi sát bike trong hành động lên xe. |
| 31:07,5 trở đi | Player ngồi lái lại; cảnh chuyển động tiến tiếp. |
| 31:00,0→31:02,5→31:04,5 | HUD rank đọc được8→9→10. Đây là hậu quả mất vị trí trong tình huống cụ thể. |
| 31:06,5–31:08,0 | Người đi bộ áo sáng đi ngang đường cạnh bike/remounting rider. Chứng minh pedestrian baseline có thật; chưa chứng minh collider/AI/damage của họ. |
| 34:59,5 | Đối thủ xanh áp sát phía phải player. |
| 35:00,0;35:01,0/01,5;35:02,0 | Các frame thấy cánh tay player vươn sang phải trong khi hai xe vẫn chạy. Không đếm các pose thành số hit riêng, không suy ra input/cooldown/damage. |
| 35:02,5 trở đi | Đối thủ xanh chạy phía trước; player tiếp tục đuổi và điều chỉnh lane/cua. |

Với0,5s giữa các mẫu: bắt đầu separation nằm trong(30:59,5;31:00,0], trở lại riding nằm trong(31:07,0;31:07,5]. Recovery tình huống này khoảng **7–8giây**, đại diện7,5±0,5giây; không phải hằng số mọi crash. Thời gian phụ thuộc khoảng rider/bike, tumble, đứng, chạy và remount. Cần frame-by-frame/input/native trace nếu muốn chốt hit window hoặc duration chính xác hơn.

Các clip đã sẵn cho review side-by-side với capture mới Racing Bois. Chưa có suy luận parity chỉ từ việc hai bản đều có tấn công/crash/recovery. Side-by-side phải giữ nhãn bản gốc/bản mới, timestamp/source offset và phân biệt capture có setup controlled với gameplay tự nhiên.

## Capture Racing Bois và đối chiếu đã tạo

[gameplay-combat-recovery.mp4](unity/gameplay-combat-recovery.mp4) mã hóa từ đúng360PNG của Unity Editor,1104×506,30frame/giây,12giây, không audio. Đây là export có bước mô phỏng cố định:2tick60Hz cho mỗi frame. **30fps encoded không phải số đo realtime FPS, browser FPS hay thời gian render.**

Setup do capture harness cung cấp: hai rider trong arena, một traffic xe ngược chiều đặt ở110m, seed1996; sau initial placement chỉ phát input. Không dùng capture controlled này làm đại diện mọi va chạm tự nhiên.

[visual-capture-summary.json](unity/visual-capture-summary.json) giữ SHA timeline, digest của manifest360frame theo thứ tự, SHA/video metadata và toàn bộ mode transitions. Script tái lập encode: `python tools/p03p04/encode_gameplay_comparison.py`.

| Frame / video time | Tick / state được timeline xác nhận |
|---|---|
| 0 /0,000s | Tick2, Attacking; clip đã chạy2tick đầu, video offset0 không phải sim tick0 |
| 4 /0,133s | Tick10, Hit; health4096→3648, phù hợp cú đầu448healthunits |
| 33 /1,100s | Nhìn thấy hai rider vươn tay về phía nhau trong lúc xe còn tiến; HUD ghi đang ra đòn |
| 72 /2,400s | Tick146, Falling; collision với traffic, health1412/bike69 |
| 93 /3,100s | Tick188, Detached; separation dọc rider/bike khoảng7,343m |
| 102 /3,400s | Tick206, Running; nhìn thấy người đứng/chạy và bike nằm phía trước |
| 157 /5,233s | Tick316, Remounting; rider đã tới bike, separation0 |
| 187 /6,233s | Tick376, Attacking sau remount; health4096/bike69. Frame186 vẫn Remounting |

Khoảng sampled Falling→trở lại state lái/attack là **3,833s** (115frame/230tick); frame sampling phân giải1/30s. Hai timing nguồn khác nhau: original trường hợp đã quan sát7–8s, Racing Bois controlled case3,833s. Bản mới có đoạn Falling/Detached ngắn hơn và khoảng chạy về bike trong arena nhỏ; không kết luận recovered duration giống nhau.

Research-only side-by-side nằm trong folder gitignored:

- [side-by-side-recovery.mp4](reference/side-by-side-recovery.mp4):12s, original30:58–31:10 so với toàn bộ capture mới, giữ tốc độ thật, không retime; crash không được ép đồng bộ cùng timestamp.
- [side-by-side-combat.mp4](reference/side-by-side-combat.mp4):2,4s, original34:59,5–35:01,9 so với capture0–2,4s trước crash mới. Bên gốc chỉ thấy pose; bên mới có timeline health, không suy damage gốc từ hình.

Đã xem frame native30/33/72/83/102/157/186 và các frame của video đã encode ở4,0/6,5s recovery,1,1s combat. Đã sửa layout label/footer sau lượt encode đầu; bản cuối hiển thị đầy đủ tên hai nguồn và giới hạn khác điều kiện. Hai panel giữ aspect ratio, vì thế bản mới dạng widescreen có letterbox trong panel4:3.

Quan sát hình ảnh: bản mới đọc được arm extension, rider/bike tách rời, đường chạy về và remount. So với reference, rider trong góc máy mới nhỏ hơn theo chiều cao khung hình, pose đơn giản hơn, và roadside đang thưa theo mức graybox; chưa đạt độ phong phú/thẩm mỹ final art. Kết quả đối chiếu chứng minh chuỗi state có hình ảnh hoạt động, không xác nhận timing/feel/art ngang bản gốc.
