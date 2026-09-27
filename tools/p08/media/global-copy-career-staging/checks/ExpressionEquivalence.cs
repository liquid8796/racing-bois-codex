using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.Json;
using RacingBois.Client.Application;

static class Program {
 private static readonly HashSet<string> UsedKeys = new HashSet<string>();
 private static string T(string key) { UsedKeys.Add(key); return UiText.Get("VI",key); }
 private static string F(string key,params UiTextArgument[] args) { UsedKeys.Add(key); return UiText.Format("VI",key,args); }
 private static UiTextArgument A(string name,string value) => new UiTextArgument(name,value);
 private static string ErrorText(string code) => "[error:"+code+"]";
 private static string SuccessText(string notice) => "[notice:"+notice+"]";
 private static void Require(bool condition,string failure) { if(!condition) throw new InvalidOperationException(failure); }
 private static void Main(string[] args) {
  long assertions=0; int scenarios=0;
  foreach(string culture in new[] {"vi-VN","en-US","de-DE","fr-FR"}) {
   CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo(culture);
   for(int flags=0;flags<512;flags++) {
    var s=new Scenario();
    s.inRoom=(flags&1)!=0; s.equipped=(flags&2)!=0; s.shop=(flags&4)!=0;
    s.owned=(flags&8)!=0; s.isOwned=(flags&16)!=0; s.selected=(flags&32)!=0;
    s.available=(flags&64)!=0; s.qualified=(flags&128)!=0;
    s.bike.HasDistinctArt=(flags&256)!=0; s.inspected.HasDistinctArt=s.bike.HasDistinctArt;
    s.route.IsPlayable=(flags&256)!=0;
    s.profile.SelectedBikeId=(flags&2)!=0?s.bike.Id:"other";
    s.profile.RealmKind=flags%3==0?"offline":flags%3==1?"online":"custom{realm}";
    s.profile.DisplayName=flags%7==0?null:flags%7==1?"{credits}<name>":"Tay đua Ω";
    s.profile.Username=flags%7==2?"user{code}":"rider_01";
    s.profile.Credits=flags%5==0?int.MaxValue:flags%5==1?0:1234567;
    s.condition=flags%3==0?100:flags%3==1?0:37;
    s.level=flags%3; s.profile.LevelIndex=(flags/3)%3;
    s.session.Busy=(flags&1)!=0; s.session.ErrorCode=flags%3==0?"":flags%3==1?"network_unavailable":"{unknown}";
    s.session.Notice=flags%2==0?"view":"buy";
    s.session.Endpoint=flags%2==0?"wss://example.invalid/game":"ws://127.0.0.1:7777/";
    s.difference=flags%3==0?-12.345f:flags%3==1?0:12.345f;
    s.bike.DisplayName=flags%7==3?"Bike {cost}":"Spark 450";
    s.inspected.DisplayName=s.bike.DisplayName; s.selectedDefinition.DisplayName=s.bike.DisplayName;
    s.current.DisplayName=flags%7==4?"Apex <R5>":"Spark 450";
    s.code=flags%7==5?null:flags%7==6?"{bike}{cost}":"invalid_operation";
    s.value=flags%2==0?"2026-09-28T01:02:03Z":"not-a-timestamp";
    for(int site=0;site<Sites.Length;site++) {
     string original=Original(site,s),replacement=Replacement(site,s);
     Require(original==replacement,"VI expression mismatch at source span "+Sites[site]+" culture "+culture+" flags "+flags);
     assertions++;
    }
    scenarios++;
   }
  }
  var empty=new Scenario(); empty.profile=null;
  int summary=Array.IndexOf(Sites,8182);
  Require(Original(summary,empty)==Replacement(summary,empty),"Null profile summary changed.");assertions++;
  string opaque="{bike}<b>name</b>";
  Require(UiText.Format("VI","career.garage.previewTooltip",new UiTextArgument("bike",opaque))=="Xem trước "+opaque,"Inserted values were rescanned.");assertions++;
  foreach(string failure in new[]{"missing","extra","duplicate"}) {
   bool rejected=false;
   try {
    if(failure=="missing") UiText.Format("VI","career.garage.previewTooltip");
    else if(failure=="extra") UiText.Format("VI","career.garage.previewTooltip",A("bike","x"),A("extra","y"));
    else UiText.Format("VI","career.garage.previewTooltip",A("bike","x"),A("bike","y"));
   } catch(ArgumentException) { rejected=true; }
   Require(rejected,"Expected named-argument rejection: "+failure);assertions++;
  }
  Require(UsedKeys.Count==156,"Not every Career/common template variant was exercised.");
  var result=new {passed=true,scope="Managed original-vs-template VI expression equivalence using real staged UiText formatter; not native UI, translation or layout acceptance.",
   expressionSites=Sites.Length,compositionSites=30,cultures=4,scenarios,assertions,templateKeysCovered=UsedKeys.Count,
   opaqueArgumentControlPassed=true,namedArgumentNegativeControls=3};
  string json=JsonSerializer.Serialize(result,new JsonSerializerOptions {WriteIndented=true});
  if(args.Length==1) File.WriteAllText(args[0],json+"\n");
  Console.WriteLine(json);
 }
 private static readonly int[] Sites={2592,2618,2652,2683,2727,2759,2818,2943,3542,3745,4010,4100,6165,8182,8553,8612,11406,11496,11651,11762,12456,13136,13670,14301,14646,15230,15776,15912,16208,16650,16772,17567,17673,17713,18189,18294,19009,19406,20671,21240,21679,21959,22028,22413,22483,22890,22914,23380,23613,23929,24214,24813,24900,25285,25320,25335,25345,27226,27425,27593,27905,28206,28339,29474,29547,29913,30290,30857,30993,31173,31247,31423,32023,32255,32341,32615,32729,32937,33040,33312,33464,33652,33759,33982,34116,34302,34565,34729,34768,35209,35244,35409,35447,35680,35841,35988,36066,36265,36515,36635,36808,39166,39213,39249,39314,39368,39427,39492,39564,39651,39737,39810,39950,40049,40113,40188,40380,40411,40443,40493,40565,40639,40784,41267,41374,41491,41620,41762,41887,42024,42125,42252,42367,42481,42576,42683,42821,42953,43085,43183,43298};
 private static string Original(int site,Scenario s) {
  var profile=s.profile; var session=s.session; var bike=s.bike; var inspected=s.inspected;
  var selectedDefinition=s.selectedDefinition; var current=s.current; var tuning=s.tuning; var route=s.route; var entry=s.entry;
  bool inRoom=s.inRoom,equipped=s.equipped,shop=s.shop,owned=s.owned,isOwned=s.isOwned,selected=s.selected,available=s.available,qualified=s.qualified;
  int condition=s.condition,tradeValue=s.tradeValue,level=s.level; float difference=s.difference; string code=s.code,value=s.value;
  switch(site) {
   case 0: return "GARAGE";
   case 1: return "CỬA HÀNG";
   case 2: return "TAY ĐUA";
   case 3: return "HÀNH TRÌNH";
   case 4: return "GIAO DỊCH";
   case 5: return "TÀI KHOẢN";
   case 6: return "XONG";
   case 7: return "Kết nối hồ sơ để lưu hành trình của bạn.";
   case 8: return "XÁC NHẬN";
   case 9: return "HỦY";
   case 10: return "LÀM MỚI";
   case 11: return "THỬ LẠI";
   case 12: return "Đang chờ máy chủ xác nhận. Vui lòng đợi.";
   case 13: return profile == null ? "Kết nối một hồ sơ để bắt đầu hành trình." :
                profile.DisplayName + "   /   $" + profile.Credits.ToString("N0") + "   /   CẤP " + (profile.LevelIndex + 1) + "   /   " +
                (profile.RealmKind == "offline" ? "HỒ SƠ LAN · TÁCH BIỆT ONLINE" : "HỒ SƠ " + profile.RealmKind.ToUpperInvariant());
   case 14: return "MÁY CHỦ  " + session.Endpoint;
   case 15: return session.Busy ? "ĐANG XỬ LÝ · Chờ máy chủ xác nhận…" : !string.IsNullOrEmpty(session.ErrorCode) ? ErrorText(session.ErrorCode) : SuccessText(session.Notice);
   case 16: return "MỖI HÀNH TRÌNH CẦN MỘT HỒ SƠ.";
   case 17: return "Hồ sơ được lưu trên máy chủ đang chọn. Khách mới và chế độ tập offline không tích lũy vào garage này.";
   case 18: return "KẾT NỐI HỒ SƠ";
   case 19: return "ĐĂNG NHẬP TÀI KHOẢN";
   case 20: return "XE CỦA BẠN";
   case 21: return "Garage chưa có xe.";
   case 22: return "Xem trước " + bike.DisplayName;
   case 23: return "Ảnh xe đang chờ bản render 3D được kiểm tra.";
   case 24: return bike.Id == profile.SelectedBikeId ? "ĐANG DÙNG" : "ĐÃ SỞ HỮU";
   case 25: return "TÌNH TRẠNG XE";
   case 26: return "Chọn xe để xem trước. Thay đổi xe dùng\nkhi máy chủ xác nhận.";
   case 27: return inRoom ? "Rời phòng trước khi đổi hoặc sửa xe." : "Phiên khách không thực hiện giao dịch hồ sơ.";
   case 28: return equipped ? "ĐANG DÙNG" : "CHỌN XE";
   case 29: return condition == 100 ? "XE NGUYÊN VẸN" : "SỬA XE · $" + inspected.RepairCredits.ToString("N0");
   case 30: return "Sửa " + inspected.DisplayName + " về 100% với $" + inspected.RepairCredits.ToString("N0") + "?";
   case 31: return "HÀNH TRÌNH ĐÃ DỪNG · Xe hỏng và quỹ không đủ sửa.";
   case 32: return "BẮT ĐẦU LẠI HÀNH TRÌNH";
   case 33: return "Bắt đầu lại từ đầu? Xe và chiến dịch hiện tại sẽ mất. Spark 450 trở về nguyên vẹn, quỹ $0. Tài khoản và lịch sử giao dịch được giữ lại.";
   case 34: return shop ? "TÌM MỘT CẤU HÌNH PHÙ HỢP." : "XE CỦA BẠN.";
   case 35: return "Chọn một mẫu để so sánh với xe đang dùng. Giá, quyền sở hữu và tình trạng do máy chủ xác nhận.";
   case 36: return "Garage chưa có xe.";
   case 37: return (bike.CatalogIndex + 1).ToString("00") + "   " + bike.DisplayName + "\n" +
                    (owned ? "ĐÃ SỞ HỮU" : !bike.HasDistinctArt ? "CHƯA MỞ" : "$" + bike.PriceCredits.ToString("N0")) +
                    (bike.Id == profile.SelectedBikeId ? " · ĐANG DÙNG" : "");
   case 38: return isOwned ? "TÌNH TRẠNG " + condition + "%" + (equipped ? " · ĐANG DÙNG" : " · ĐÃ SỞ HỮU") : "$" + inspected.PriceCredits.ToString("N0") + " · " + (inspected.HasDistinctArt ? "CÓ THỂ MUA" : "CHƯA MỞ");
   case 39: return "SO VỚI " + current.DisplayName.ToUpperInvariant() + "\nGiới hạn tốc độ " + difference.ToString("+0.#;-0.#;0", CultureInfo.InvariantCulture) + " km/h\nHệ số 1× lấy Spark 450 làm mốc. Đây là thông số thiết kế trong game.";
   case 40: return equipped ? "ĐANG DÙNG" : "CHỌN XE";
   case 41: return "SỬA XE · $" + inspected.RepairCredits.ToString("N0");
   case 42: return "Sửa " + selectedDefinition.DisplayName + " về 100% với $" + selectedDefinition.RepairCredits.ToString("N0") + "?";
   case 43: return "MUA THÊM · $" + inspected.PriceCredits.ToString("N0");
   case 44: return "Mua " + selectedDefinition.DisplayName + " với $" + selectedDefinition.PriceCredits.ToString("N0") + "?";
   case 45: return "ĐỔI XE";
   case 46: return "Bán chiếc đang dùng với $" + tradeValue.ToString("N0") + " và mua " + selectedDefinition.DisplayName + " với $" + selectedDefinition.PriceCredits.ToString("N0") + "?";
   case 47: return inRoom ? "Rời phòng trước khi đổi, mua hoặc sửa xe." : "Phiên khách không thực hiện giao dịch hồ sơ.";
   case 48: return "XEM 3D";
   case 49: return "Xem thiết kế " + bike.DisplayName + " và trở lại hồ sơ.";
   case 50: return "GIỚI HẠN " + (tuning.MaximumSpeedMillimetersPerSecond * .0036).ToString("0.#", CultureInfo.InvariantCulture) + " km/h" +
                "  ·  TĂNG TỐC ×" + (tuning.EnginePermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture) +
                "\nPHANH " + (tuning.BrakeDeceleration / 1000.0).ToString("0.#", CultureInfo.InvariantCulture) + " m/s²" +
                "  ·  BÁM CUA ×" + (tuning.CorneringPermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture);
   case 51: return "CHỌN GƯƠNG MẶT CỦA HÀNH TRÌNH.";
   case 52: return "8 tay đua, mỗi người một phong cách. Lựa chọn thay đổi diện mạo; sức mạnh và phần thưởng giữ nguyên.";
   case 53: return "XEM BIỂU CẢM";
   case 54: return "Bình thường";
   case 55: return "Vui vẻ";
   case 56: return "Tập trung";
   case 57: return "Ảnh chân dung sẽ xuất hiện khi nội dung được tải.";
   case 58: return selected ? "ĐANG ĐỒNG HÀNH" : available ? "SẴN SÀNG LÊN ĐƯỜNG" : "CHƯA MỞ";
   case 59: return selected ? "ĐANG CHỌN" : "CHỌN TAY ĐUA";
   case 60: return "XEM TAY ĐUA";
   case 61: return "Rời phòng hiện tại trước khi đổi tay đua cho hồ sơ.";
   case 62: return "Kết nối hồ sơ đã lưu để chọn tay đua cho hành trình. Chế độ luyện tập cho phép thử mọi tay đua đã mở.";
   case 63: return "5 CẤP. 25 CHẶNG.";
   case 64: return "Top 3 ở đủ 5 tuyến để lên cấp. Chọn một chặng thuộc cấp hiện tại; kết quả luyện tập không cộng vào hồ sơ máy chủ.";
   case 65: return "CẤP " + (level + 1).ToString("00");
   case 66: return !route.IsPlayable ? "SẮP RA MẮT" : level > profile.LevelIndex ? "CHƯA MỞ" : qualified ? "ĐÃ QUA" : "ĐUA";
   case 67: return "Rời phòng hiện tại trước khi tạo chặng của hành trình.";
   case 68: return "ĐÃ HOÀN THÀNH HÀNH TRÌNH · Bạn có thể đua lại cấp hiện tại hoặc luyện tập tự do.";
   case 69: return "LỊCH SỬ GIAO DỊCH";
   case 70: return "Số dư và phần thưởng chỉ thay đổi sau khi máy chủ ghi nhận thành công.";
   case 71: return "Chưa có giao dịch.";
   case 72: return "SỐ DƯ $" + entry.Balance.ToString("N0");
   case 73: return "GIỮ LẠI HÀNH TRÌNH CỦA BẠN.";
   case 74: return "Tài khoản thuộc máy chủ này. Đăng nhập, đăng ký và đổi mật khẩu cần HTTPS. Mã khôi phục dùng một lần thay cho email; hãy tự lưu ở nơi riêng tư.";
   case 75: return "LƯU MÃ KHÔI PHỤC MỚI · Chỉ hiển thị trong lần này";
   case 76: return "MÃ KHÔI PHỤC";
   case 77: return "ĐANG ĐĂNG NHẬP: " + profile.Username;
   case 78: return "TÊN TÀI KHOẢN";
   case 79: return "MẬT KHẨU (HOẶC MẬT KHẨU MỚI KHI KHÔI PHỤC)";
   case 80: return "MÃ KHÔI PHỤC (CHỈ CẦN KHI QUÊN MẬT KHẨU)";
   case 81: return "ĐĂNG NHẬP";
   case 82: return "NÂNG CẤP HỒ SƠ";
   case 83: return "ĐỔI MẬT KHẨU BẰNG MÃ";
   case 84: return "Dán mật khẩu và mã được hỗ trợ. Đăng nhập sẽ kết thúc phiên đang mở trước khi đổi hồ sơ.";
   case 85: return "KẾT NỐI HỒ SƠ ĐỂ ĐĂNG KÝ";
   case 86: return "Khóa hồ sơ đang lưu đã hết hạn hoặc bị thu hồi. Tài khoản đã đăng ký vẫn có thể đăng nhập hoặc khôi phục ở trên.";
   case 87: return "BỎ KHÓA HỒ SƠ ĐÃ HẾT HẠN";
   case 88: return "Bỏ khóa cũ trên máy này? Bạn sẽ không còn truy cập hồ sơ vô danh cũ bằng khóa này. Nếu đã nâng cấp tài khoản, hãy đăng nhập hoặc khôi phục tài khoản để giữ tiến trình; bản sao lưu máy chủ vẫn cần cơ chế khôi phục của chủ máy. Sau khi bỏ khóa, KẾT NỐI HỒ SƠ sẽ tạo hồ sơ mới.";
   case 89: return "ĐĂNG XUẤT MÁY NÀY";
   case 90: return "Thu hồi khóa hồ sơ trên máy này và kết thúc phiên hiện tại?";
   case 91: return "THU HỒI TẤT CẢ PHIÊN";
   case 92: return "Đăng xuất tất cả phiên của tài khoản? Bạn cần đăng nhập lại trên từng máy.";
   case 93: return "TẠO MÃ KHÔI PHỤC MỚI";
   case 94: return "Sao lưu bằng văn bản chỉ dành cho hồ sơ LAN offline; dữ liệu online được quản lý trên máy chủ.";
   case 95: return "SAO LƯU LAN OFFLINE";
   case 96: return "Bản lưu chỉ nhập lại vào hồ sơ offline này và phải qua kiểm tra máy chủ. Nội dung bản lưu có dữ liệu cá nhân; chỉ dán hoặc lưu ở nơi bạn tin cậy.";
   case 97: return "NỘI DUNG BẢN LƯU";
   case 98: return "XUẤT BẢN LƯU";
   case 99: return "NHẬP BẢN LƯU";
   case 100: return "Nhập bản lưu này? Máy chủ sẽ kiểm tra nguồn và tính hợp lệ trước khi thay thế tiến trình offline.";
   case 101: return "Đã thêm xe vào garage.";
   case 102: return "Đã đổi xe.";
   case 103: return "Xe đã được sửa về 100%.";
   case 104: return "Đã chọn xe cho chặng tới.";
   case 105: return "Đã chọn tay đua cho hành trình.";
   case 106: return "Đã nâng cấp hồ sơ. Hãy lưu mã khôi phục.";
   case 107: return "Đăng nhập thành công.";
   case 108: return "Đã tạo mã khôi phục mới. Mã cũ hết hiệu lực; hãy lưu mã mới.";
   case 109: return "Đã đổi mật khẩu. Hãy lưu mã khôi phục mới.";
   case 110: return "Đã thu hồi phiên và đăng xuất.";
   case 111: return "Đã bỏ khóa cũ trên máy này. Chọn KẾT NỐI HỒ SƠ để tạo hồ sơ mới, hoặc đăng nhập tài khoản.";
   case 112: return "Hành trình đã bắt đầu lại: Spark 450 nguyên vẹn, quỹ $0.";
   case 113: return "Đã nhập bản lưu được máy chủ xác nhận.";
   case 114: return "Bản lưu đã sẵn sàng. Chọn toàn bộ nội dung để sao chép.";
   case 115: return "Tiến trình được máy chủ xác nhận. Có thể làm mới để cập nhật.";
   case 116: return "Mua xe";
   case 117: return "Đổi xe";
   case 118: return "Sửa xe";
   case 119: return "Kết quả cuộc đua";
   case 120: return "Bắt đầu lại hành trình";
   case 121: return "Quỹ khởi đầu";
   case 122: return DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var timestamp)
                ? timestamp.ToString("dd/MM/yyyy HH:mm 'UTC'", CultureInfo.InvariantCulture)
                : "Thời gian chưa rõ";
   case 123: return "Hãy kết nối hồ sơ đã lưu hoặc đăng nhập tài khoản trước.";
   case 124: return "Đổi địa chỉ máy chủ sang wss:// để đăng nhập qua kết nối TLS.";
   case 125: return "Không nhận được phản hồi. Kiểm tra kết nối; Thử lại giữ nguyên mã giao dịch.";
   case 126: return "Tên tài khoản cần 3–24 ký tự a–z, 0–9, dấu gạch dưới hoặc gạch nối.";
   case 127: return "Mật khẩu cần 12–128 ký tự. Hãy dùng một mật khẩu dài và riêng cho tài khoản.";
   case 128: return "Hồ sơ vẫn còn xe chạy được hoặc đủ quỹ sửa xe. Làm mới garage để tiếp tục hành trình.";
   case 129: return "Xe đang chọn đã hỏng. Sửa xe trước khi đổi hoặc đua.";
   case 130: return "Bản lưu không hợp lệ hoặc đã bị thay đổi. Dùng bản xuất nguyên vẹn từ máy chủ.";
   case 131: return "Bản lưu thuộc hồ sơ hoặc máy chủ khác; không thể nhập vào hồ sơ này.";
   case 132: return "Bản lưu đã cũ. Xuất bản mới nhất để bảo toàn giao dịch hiện tại.";
   case 133: return "Xe này đã có trong garage. Làm mới để chọn xe.";
   case 134: return "Thao tác quá nhanh. Đợi một lát rồi thực hiện lại.";
   case 135: return "Quỹ chưa đủ cho giao dịch này. Hãy hoàn thành thêm chặng đua.";
   case 136: return "Tên tài khoản, mật khẩu hoặc mã khôi phục chưa đúng.";
   case 137: return "Tên tài khoản đã có người dùng. Hãy chọn tên khác.";
   case 138: return "Rời phòng đua rồi thực hiện giao dịch này.";
   case 139: return "Máy chủ chưa lưu được dữ liệu. Thử lại sau; số dư chưa được xác nhận thay đổi.";
   case 140: return "Chưa thực hiện được thao tác (" + code + "). Làm mới hồ sơ và kiểm tra dữ liệu vừa nhập.";
   default: throw new ArgumentOutOfRangeException(nameof(site));
  }
 }
 private static string Replacement(int site,Scenario s) {
  var profile=s.profile; var session=s.session; var bike=s.bike; var inspected=s.inspected;
  var selectedDefinition=s.selectedDefinition; var current=s.current; var tuning=s.tuning; var route=s.route; var entry=s.entry;
  bool inRoom=s.inRoom,equipped=s.equipped,shop=s.shop,owned=s.owned,isOwned=s.isOwned,selected=s.selected,available=s.available,qualified=s.qualified;
  int condition=s.condition,tradeValue=s.tradeValue,level=s.level; float difference=s.difference; string code=s.code,value=s.value;
  switch(site) {
   case 0: return T("career.tabs.garage");
   case 1: return T("career.tabs.shop");
   case 2: return T("career.tabs.characters");
   case 3: return T("career.tabs.campaign");
   case 4: return T("career.tabs.ledger");
   case 5: return T("career.tabs.account");
   case 6: return T("common.done");
   case 7: return T("career.summary.connectToSave");
   case 8: return T("common.confirm");
   case 9: return T("common.cancel");
   case 10: return T("common.refresh");
   case 11: return T("common.retry");
   case 12: return T("career.status.awaitingConfirmation");
   case 13: return profile == null ? T("career.summary.empty") : profile.RealmKind == "offline" ? F("career.summary.offline", A("player", profile.DisplayName), A("credits", profile.Credits.ToString("N0")), A("level", (profile.LevelIndex + 1).ToString())) : F("career.summary.realm", A("player", profile.DisplayName), A("credits", profile.Credits.ToString("N0")), A("level", (profile.LevelIndex + 1).ToString()), A("realm", profile.RealmKind.ToUpperInvariant()));
   case 14: return F("career.summary.endpoint", A("endpoint", session.Endpoint));
   case 15: return session.Busy ? T("career.status.busy") : !string.IsNullOrEmpty(session.ErrorCode) ? ErrorText(session.ErrorCode) : SuccessText(session.Notice);
   case 16: return T("career.profile.requiredTitle");
   case 17: return T("career.profile.storageHint");
   case 18: return T("career.profile.connect");
   case 19: return T("career.account.openLogin");
   case 20: return T("career.garage.ownedHeading");
   case 21: return T("career.garage.empty");
   case 22: return F("career.garage.previewTooltip", A("bike", bike.DisplayName));
   case 23: return T("career.garage.thumbnailPending");
   case 24: return bike.Id == profile.SelectedBikeId ? T("career.bike.equipped") : T("career.bike.owned");
   case 25: return T("career.garage.conditionHeading");
   case 26: return T("career.garage.previewHint");
   case 27: return inRoom ? T("career.garage.leaveRoom") : T("career.profile.guestTransactions");
   case 28: return equipped ? T("career.bike.equipped") : T("career.garage.equip");
   case 29: return condition == 100 ? T("career.garage.pristine") : F("career.garage.repairButton", A("cost", inspected.RepairCredits.ToString("N0")));
   case 30: return F("career.garage.repairConfirm", A("bike", inspected.DisplayName), A("cost", inspected.RepairCredits.ToString("N0")));
   case 31: return T("career.garage.bankruptNotice");
   case 32: return T("career.garage.restart");
   case 33: return T("career.garage.restartConfirm");
   case 34: return shop ? T("career.shop.heading") : T("career.garage.browserHeading");
   case 35: return T("career.shop.compareHint");
   case 36: return T("career.garage.empty");
   case 37: return owned ? (bike.Id == profile.SelectedBikeId ? F("career.bikeList.ownedEquipped", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName)) : F("career.bikeList.owned", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName))) : !bike.HasDistinctArt ? (bike.Id == profile.SelectedBikeId ? F("career.bikeList.lockedEquipped", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName)) : F("career.bikeList.locked", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName))) : (bike.Id == profile.SelectedBikeId ? F("career.bikeList.priceEquipped", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName), A("cost", bike.PriceCredits.ToString("N0"))) : F("career.bikeList.price", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName), A("cost", bike.PriceCredits.ToString("N0"))));
   case 38: return isOwned ? (equipped ? F("career.bikeDetail.equipped", A("condition", condition.ToString())) : F("career.bikeDetail.owned", A("condition", condition.ToString()))) : (inspected.HasDistinctArt ? F("career.bikeDetail.available", A("cost", inspected.PriceCredits.ToString("N0"))) : F("career.bikeDetail.locked", A("cost", inspected.PriceCredits.ToString("N0"))));
   case 39: return F("career.bike.compare", A("bike", current.DisplayName.ToUpperInvariant()), A("difference", difference.ToString("+0.#;-0.#;0", CultureInfo.InvariantCulture)));
   case 40: return equipped ? T("career.bike.equipped") : T("career.garage.equip");
   case 41: return F("career.garage.repairButton", A("cost", inspected.RepairCredits.ToString("N0")));
   case 42: return F("career.garage.repairConfirm", A("bike", selectedDefinition.DisplayName), A("cost", selectedDefinition.RepairCredits.ToString("N0")));
   case 43: return F("career.shop.buyButton", A("cost", inspected.PriceCredits.ToString("N0")));
   case 44: return F("career.shop.buyConfirm", A("bike", selectedDefinition.DisplayName), A("cost", selectedDefinition.PriceCredits.ToString("N0")));
   case 45: return T("career.shop.trade");
   case 46: return F("career.shop.tradeConfirm", A("tradeValue", tradeValue.ToString("N0")), A("bike", selectedDefinition.DisplayName), A("cost", selectedDefinition.PriceCredits.ToString("N0")));
   case 47: return inRoom ? T("career.shop.leaveRoom") : T("career.profile.guestTransactions");
   case 48: return T("career.bike.preview");
   case 49: return F("career.bike.previewTooltip", A("bike", bike.DisplayName));
   case 50: return F("career.bike.stats", A("speed", (tuning.MaximumSpeedMillimetersPerSecond * .0036).ToString("0.#", CultureInfo.InvariantCulture)), A("acceleration", (tuning.EnginePermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture)), A("braking", (tuning.BrakeDeceleration / 1000.0).ToString("0.#", CultureInfo.InvariantCulture)), A("cornering", (tuning.CorneringPermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture)));
   case 51: return T("career.characters.heading");
   case 52: return T("career.characters.selectionHint");
   case 53: return T("career.characters.expressionLabel");
   case 54: return T("career.characters.expressionNeutral");
   case 55: return T("career.characters.expressionHappy");
   case 56: return T("career.characters.expressionFocused");
   case 57: return T("career.characters.portraitPending");
   case 58: return selected ? T("career.characters.accompanying") : available ? T("career.characters.ready") : T("career.state.locked");
   case 59: return selected ? T("career.characters.selected") : T("career.characters.choose");
   case 60: return T("career.characters.inspect");
   case 61: return T("career.characters.leaveRoom");
   case 62: return T("career.characters.connectProfile");
   case 63: return T("career.campaign.heading");
   case 64: return T("career.campaign.progressionHint");
   case 65: return F("career.campaign.level", A("level", (level + 1).ToString("00")));
   case 66: return !route.IsPlayable ? T("career.campaign.comingSoon") : level > profile.LevelIndex ? T("career.state.locked") : qualified ? T("career.campaign.qualified") : T("career.campaign.race");
   case 67: return T("career.campaign.leaveRoom");
   case 68: return T("career.campaign.complete");
   case 69: return T("career.ledger.heading");
   case 70: return T("career.ledger.authorityHint");
   case 71: return T("career.ledger.empty");
   case 72: return F("career.ledger.balance", A("balance", entry.Balance.ToString("N0")));
   case 73: return T("career.account.heading");
   case 74: return T("career.account.securityHint");
   case 75: return T("career.account.newRecoveryNotice");
   case 76: return T("career.account.recoveryCodeLabel");
   case 77: return F("career.account.loggedIn", A("username", profile.Username));
   case 78: return T("career.account.usernameLabel");
   case 79: return T("career.account.passwordLabel");
   case 80: return T("career.account.recoveryInputLabel");
   case 81: return T("career.account.login");
   case 82: return T("career.account.register");
   case 83: return T("career.account.recover");
   case 84: return T("career.account.pasteHint");
   case 85: return T("career.account.connectToRegister");
   case 86: return T("career.account.expiredCredentialHint");
   case 87: return T("career.account.forgetCredential");
   case 88: return T("career.account.forgetCredentialConfirm");
   case 89: return T("career.account.logout");
   case 90: return T("career.account.logoutConfirm");
   case 91: return T("career.account.logoutAll");
   case 92: return T("career.account.logoutAllConfirm");
   case 93: return T("career.account.rotateRecovery");
   case 94: return T("career.backup.onlineRestriction");
   case 95: return T("career.backup.heading");
   case 96: return T("career.backup.privacyHint");
   case 97: return T("career.backup.contentLabel");
   case 98: return T("career.backup.export");
   case 99: return T("career.backup.import");
   case 100: return T("career.backup.importConfirm");
   case 101: return T("career.notice.buy");
   case 102: return T("career.notice.trade");
   case 103: return T("career.notice.repair");
   case 104: return T("career.notice.equip");
   case 105: return T("career.notice.character");
   case 106: return T("career.notice.register");
   case 107: return T("career.notice.login");
   case 108: return T("career.notice.rotateRecovery");
   case 109: return T("career.notice.recover");
   case 110: return T("career.notice.logout");
   case 111: return T("career.notice.forget");
   case 112: return T("career.notice.restart");
   case 113: return T("career.notice.import");
   case 114: return T("career.notice.export");
   case 115: return T("career.notice.default");
   case 116: return T("career.ledger.reasonBuy");
   case 117: return T("career.ledger.reasonTrade");
   case 118: return T("career.ledger.reasonRepair");
   case 119: return T("career.ledger.reasonRace");
   case 120: return T("career.ledger.reasonRestart");
   case 121: return T("career.ledger.reasonOpening");
   case 122: return DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var timestamp) ? timestamp.ToString("dd/MM/yyyy HH:mm 'UTC'", CultureInfo.InvariantCulture) : T("career.ledger.unknownTime");
   case 123: return T("career.error.authRequired");
   case 124: return T("career.error.httpsRequired");
   case 125: return T("career.error.networkUnavailable");
   case 126: return T("career.error.invalidUsername");
   case 127: return T("career.error.invalidPassword");
   case 128: return T("career.error.notBankrupt");
   case 129: return T("career.error.repairRequired");
   case 130: return T("career.error.invalidSave");
   case 131: return T("career.error.foreignSave");
   case 132: return T("career.error.staleSave");
   case 133: return T("career.error.alreadyOwned");
   case 134: return T("career.error.rateLimited");
   case 135: return T("career.error.insufficientCredits");
   case 136: return T("career.error.invalidCredentials");
   case 137: return T("career.error.usernameUnavailable");
   case 138: return T("career.error.profileBusy");
   case 139: return T("career.error.storageUnavailable");
   case 140: return F("career.error.unknown", A("code", code));
   default: throw new ArgumentOutOfRangeException(nameof(site));
  }
 }
}
sealed class Scenario {
 public Profile profile=new Profile(); public Session session=new Session();
 public Bike bike=new Bike(),inspected=new Bike(),selectedDefinition=new Bike(),current=new Bike();
 public Tuning tuning=new Tuning(); public Route route=new Route(); public Entry entry=new Entry();
 public bool inRoom,equipped,shop,owned,isOwned,selected,available,qualified;
 public int condition=37,tradeValue=12345,level=0; public float difference=0; public string code="x",value="";
}
sealed class Profile { public string DisplayName="rider",RealmKind="offline",SelectedBikeId="spark",Username="rider"; public int Credits=1234567,LevelIndex=0; }
sealed class Session { public string Endpoint="",ErrorCode="",Notice=""; public bool Busy; }
sealed class Bike { public string Id="spark",DisplayName="Spark 450"; public bool HasDistinctArt=true; public int CatalogIndex=0,PriceCredits=2147483647,RepairCredits=12345; }
sealed class Tuning { public int MaximumSpeedMillimetersPerSecond=54321,EnginePermille=1234,BrakeDeceleration=6789,CorneringPermille=987; }
sealed class Route { public bool IsPlayable=true; }
sealed class Entry { public int Balance=1234567; }
