# Môi trường thực tế và MCP

Kiểm tra read-only ngày 2026-09-21 (Asia/Bangkok).

| Thành phần | Bằng chứng | Trạng thái |
|---|---|---|
| Project | `D:\Project\Unity\racing-bois` | Đúng workspace được người dùng cung cấp |
| Unity | `ProjectSettings/ProjectVersion.txt`: 6000.5.7f1, revision 017862109af0 | Editor có chạy |
| Unity MCP | Instance `racing-bois@5c91c5b8`, bridge 127.0.0.1:6400 | Resource và read_console/get_hierarchy trả thành công |
| MCP readiness | Lần đầu stale_status; đọc lại ready_for_tools=true, không compile/play | Kết nối được, không biến trạng thái transient thành blocker |
| Scene | Scene chưa lưu, Main Camera + Directional Light | Chưa có gameplay |
| Assets/build scenes | Không file trong Assets, EditorBuildSettings m_Scenes=[] | Project khởi tạo |
| Render pipeline | GraphicsSettings m_CustomRenderPipeline fileID=0, chưa URP package | Built-in hiện tại; URP mới là đề xuất |
| Unity packages | com.coplaydev.unity-mcp git main; com.unity.multiplayer.center 1.0.1 | Multiplayer Center không chứng minh có transport/backend |
| Console | 2 warnings: Input Manager deprecated, Dynamic Batching deprecated | Chưa thấy Error trong response; không có test/build game để xác nhận |
| Web module | PlaybackEngines/WebGLSupport tồn tại | Đã có module, chưa build Web |
| Server module | Chỉ thấy WebGLSupport và windowsstandalonesupport | Chưa xác minh Linux Dedicated Server |
| Blender | `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` tồn tại | Chưa chạy Blender trong khảo sát |
| Blender MCP | Không tool Blender trong tool catalog hiện tại; plugin search Blender trả rỗng; không listener 9876/9877 tại thời điểm kiểm tra | Chưa xác nhận kết nối; không kết luận không có ở mọi cấu hình khác |
| CPU/GPU | i7-11800H, 8 cores/16 logical; RTX 3070 Laptop GPU | Chỉ inventory phần cứng, chưa benchmark |
| RAM | Win32_ComputerSystem TotalPhysicalMemory=68,477,296,640 bytes | Khoảng 63.8 GiB |
| OCI | Chưa có target VM được gắn với Racing Bois | Chưa SSH, chưa đổi firewall, chưa triển khai |

Raw receipt: [unity-mcp-receipt.json](unity-mcp-receipt.json). Nguồn cục bộ: Packages/manifest.json, ProjectSettings, CIM process/hardware, directory/module inventory. Không đưa credential/config secret vào hồ sơ.

Kết luận: Unity MCP dùng được để bắt đầu phase nền tảng. Blender MCP cần được kết nối và thử round-trip. Khảo sát này không tự cài thêm MCP hoặc thay đổi Unity project settings vì phạm vi hiện tại là reverse và plan.
