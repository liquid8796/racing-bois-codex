namespace RacingBois.Client.Presentation
{
    internal static class MultiplayerCopy
    {
        public static string Error(string message)
        {
            const string prefix="Máy chủ từ chối: ";
            if(string.IsNullOrEmpty(message)||!message.StartsWith(prefix,System.StringComparison.Ordinal))return message;
            switch(message.Substring(prefix.Length))
            {
                case "room_full": return "Phòng đã đủ người. Hãy chọn phòng khác hoặc tạo phòng mới.";
                case "room_not_found": return "Không tìm thấy phòng. Kiểm tra lại mã hoặc làm mới danh sách.";
                case "room_started": case "late_join_closed": return "Cuộc đua đã bắt đầu. Bạn có thể vào sau khi phòng trở về trạng thái chờ.";
                case "host_only": return "Chỉ chủ phòng có thể thực hiện thao tác này.";
                case "not_ready": return "Tất cả tay đua cần kết nối và sẵn sàng trước khi bắt đầu.";
                case "invalid_name": return "Tên cần có từ 1 đến 24 ký tự và không chứa ký tự điều khiển.";
                case "room_settings": return "Kiểm tra tên phòng và số đối thủ máy.";
                case "course_unavailable": return "Tuyến đường này đang được phát triển. Hãy chọn Canyon Run.";
                case "campaign_locked": return "Cấp này chưa mở cho hồ sơ của bạn. Hãy chọn cấp đã mở trong hành trình.";
                case "repair_required": return "Xe đã hỏng. Rời phòng và sửa xe trong garage trước khi xuất phát.";
                case "profile_busy": return "Hồ sơ đang có cuộc đua chưa lưu xong. Chờ kết quả rồi thử lại.";
                case "profile_revoked": return "Phiên hồ sơ đã hết hạn hoặc được thu hồi. Vào tài khoản để đăng nhập lại.";
                case "already_in_room": return "Bạn đang ở một phòng. Hãy rời phòng đó trước.";
                case "profile_in_room": return "Hồ sơ này đang giữ chỗ ở phiên khác. Dùng Khách mới để thêm một người chơi riêng.";
                case "profile_unavailable": case "profile_storage_unavailable": return "Chưa đọc được hồ sơ trên máy chủ. Hãy thử lại sau hoặc chọn Khách mới.";
                case "resume_expired": return "Thời gian giữ chỗ đã hết. Hãy kết nối lại và vào một phòng mới.";
                case "resume_owner": case "session_replaced": return "Phiên đã được mở ở nơi khác. Chọn Khách mới để chơi riêng.";
                case "version_mismatch": return "Bản game và máy chủ khác phiên bản. Tải lại trang hoặc cập nhật gói LAN.";
                case "server_full": case "hello_capacity": case "profile_capacity": return "Máy chủ đang đầy. Hãy thử lại sau.";
                case "room_capacity": return "Máy chủ đã đủ phòng. Hãy vào một phòng còn chỗ.";
                case "persistence_pending": case "start_pending": return "Máy chủ đang chuẩn bị. Vui lòng chờ một chút.";
                case "persistence_queue_full": case "persistence_unavailable": return "Máy chủ đang bận lưu dữ liệu. Hãy thử lại sau.";
                case "result_save_retry": return "Máy chủ đang thử lưu lại kết quả. Giữ phiên này để nhận xác nhận.";
                case "start_cancelled": return "Đếm ngược đã hủy vì thành viên hoặc chủ phòng thay đổi.";
                case "result_required": return "Cuộc đua chưa kết thúc. Vui lòng chờ kết quả chính thức.";
                case "command_rate": return "Bạn thao tác quá nhanh. Chờ một chút rồi thử lại.";
                case "not_room_member": return "Bạn không còn ở phòng này. Hãy làm mới danh sách và vào lại.";
                default: return "Không thực hiện được yêu cầu này. Hãy thử lại hoặc kết nối lại máy chủ.";
            }
        }
    }
}
