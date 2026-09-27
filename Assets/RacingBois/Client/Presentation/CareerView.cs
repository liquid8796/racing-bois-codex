using System;
using System.Collections.Generic;
using System.Globalization;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    /// <summary>Career UI emits intents only. Prices are shared definitions; balances and ownership come from the server.</summary>
    public sealed class CareerView : MonoBehaviour
    {
        public event Action<CareerIntent> CommandRequested;
        public event Action RefreshRequested, RetryRequested, ConnectRequested, Closed;
        public event Action<int, int> RaceRequested;
        public event Action<int> ShowcaseRequested;
        public event Action<int> SelectedBikePreviewRequested, SelectedCharacterPreviewRequested;
        public event Action<bool> PreviewVisibilityChanged;
        private readonly UiBindingScope bindings = new UiBindingScope();
        private readonly Dictionary<string, Vector2> scrollByTab = new Dictionary<string, Vector2>();
        [SerializeField] private Sprite[] bikeThumbnails = new Sprite[BikeCatalog.Count];
        private string accountUsername = "", inspectedBikeId = "", inspectedCharacterId = "";
        private CareerSession session;
        private VisualElement root, surface, body, tabs, confirmation, actions, footer;
        private Label summary, status, endpointLabel, confirmationText;
        private Button close, retry, refresh, confirm;
        private readonly List<Button> tabButtons = new List<Button>();
        private readonly List<VisualElement> disabledBehind = new List<VisualElement>();
        private VisualElement previousFocus;
        private CareerIntent pendingConfirmation;
        private string selectedTab = "garage", renderedTab = "";
        private int portraitState;
        private int consumedBackFrame = -1;
        private bool inRoom, guest;
        private TextField password, recovery, exportText;
        public bool IsOpen => root != null && root.style.display.value != DisplayStyle.None;

        public void Initialize(UIDocument document, CareerSession application)
        {
            if (root != null) return;
            session = application; surface = document.rootVisualElement.Q("surface");
            root = new VisualElement { name = "career", focusable = true }; root.AddToClassList("career-overlay");
            var header = Row("career-heading");
            header.Add(Text("RACING BOIS", "career-wordmark"));
            tabs = Row("career-tabs");
            AddTab("garage", "GARAGE"); AddTab("shop", "CỬA HÀNG"); AddTab("characters", "TAY ĐUA"); AddTab("campaign", "HÀNH TRÌNH");
            AddTab("ledger", "GIAO DỊCH"); AddTab("account", "TÀI KHOẢN"); header.Add(tabs);
            close = Button("XONG", Close, "career-close"); close.name = "career-close"; header.Add(close); root.Add(header);
            summary = Text("Kết nối hồ sơ để lưu hành trình của bạn.", "career-summary"); root.Add(summary);
            endpointLabel = Text("", "career-endpoint"); root.Add(endpointLabel);
            body = new VisualElement { name = "career-content" }; body.AddToClassList("career-body"); root.Add(body);
            confirmation = new VisualElement { name = "career-confirmation" }; confirmation.AddToClassList("career-confirmation");
            confirmationText = Text("", "description"); confirmation.Add(confirmationText);
            var confirmationActions = Row("career-actions");
            confirm = Button("XÁC NHẬN", () => { var request = pendingConfirmation; HideConfirmation(); CommandRequested?.Invoke(request); }, "primary");
            confirmationActions.Add(confirm); confirmationActions.Add(Button("HỦY", HideConfirmation, "secondary")); confirmation.Add(confirmationActions); root.Add(confirmation);
            footer = Row("career-footer"); status = Text("", "career-status"); footer.Add(status);
            actions = Row("career-actions"); refresh = Button("LÀM MỚI", () => RefreshRequested?.Invoke(), "small-button");
            retry = Button("THỬ LẠI", () => RetryRequested?.Invoke(), "small-button"); actions.Add(refresh); actions.Add(retry); footer.Add(actions); root.Add(footer);
            surface.Add(root); root.style.display = DisplayStyle.None; confirmation.style.display = DisplayStyle.None;
            bindings.Register<NavigationCancelEvent>(root, e => { if (HandleBack()) { e.StopImmediatePropagation(); root.panel?.focusController.IgnoreEvent(e); } });
            bindings.Register<KeyDownEvent>(root, e =>
            {
                if (e.keyCode == KeyCode.Escape) { HandleBack(); e.StopImmediatePropagation(); root.panel?.focusController.IgnoreEvent(e); }
            }, TrickleDown.TrickleDown);
            // Keep keyboard focus inside the modal even if UI Toolkit traverses an underlying control.
            bindings.Register<FocusInEvent>(surface, e =>
            {
                if (IsOpen && root.enabledInHierarchy && e.target is VisualElement focused && focused != root && !root.Contains(focused))
                    root.schedule.Execute(() => { if (IsOpen && root.enabledInHierarchy) close.Focus(); });
            });
            session.Changed += Render;
        }

        public void Open(bool isConnected, bool hasRoom, bool isGuest = false)
        {
            inRoom = hasRoom; guest = isGuest;
            if (!IsOpen)
            {
                previousFocus = surface.panel?.focusController.focusedElement as VisualElement;
                foreach (var name in new[] { "menu", "multiplayer", "settings-open", "career-open", "gallery-open", "practice-open" })
                { var element = surface.Q(name); if (element != null && element.enabledSelf) { disabledBehind.Add(element); element.SetEnabled(false); } }
            }
            surface.AddToClassList("career-is-open");
            root.style.display = DisplayStyle.Flex; root.BringToFront(); HideConfirmation(); Render(); root.Focus();
        }
        public void Close()
        {
            if (!IsOpen) return;
            if (session.Busy) { status.text = "Đang chờ máy chủ xác nhận. Vui lòng đợi."; return; }
            ClearSecrets(); root.style.display = DisplayStyle.None; HideConfirmation(); PreviewVisibilityChanged?.Invoke(false);
            surface.RemoveFromClassList("career-is-open");
            foreach (var element in disabledBehind) element.SetEnabled(true); disabledBehind.Clear();
            session.ClearSensitiveOutput();
            if (previousFocus != null && previousFocus.enabledInHierarchy) previousFocus.Focus();
            Closed?.Invoke();
        }
        public bool HandleBack()
        {
            if (consumedBackFrame == Time.frameCount) return true;
            if (!IsOpen) return false;
            consumedBackFrame = Time.frameCount;
            if (pendingConfirmation != null) HideConfirmation(); else Close();
            return true;
        }
        public void SetConnectionState(bool isConnected, bool hasRoom)
        {
            if (inRoom == hasRoom) return;
            inRoom = hasRoom;
            Render();
        }
        public void RefreshPresentation() => Render();
        /// <summary>Only actual rendered bike sprites belong here; absent captures stay visibly pending in QA.</summary>
        public void SetBikeThumbnails(IReadOnlyList<Sprite> thumbnails)
        {
            bikeThumbnails = new Sprite[BikeCatalog.Count];
            if (thumbnails != null)
                for (int i = 0; i < Math.Min(thumbnails.Count, bikeThumbnails.Length); i++) bikeThumbnails[i] = thumbnails[i];
            Render();
        }
        private void AddTab(string id, string label)
        {
            var button = Button(label, () => { CaptureScroll(); ClearSecrets(); selectedTab = id; HideConfirmation(); Render(); }, "career-tab");
            button.name = "career-tab-" + id; tabs.Add(button); tabButtons.Add(button);
        }
        private void Render()
        {
            if (!IsOpen) return;
            var profile = session.Profile;
            summary.text = profile == null ? "Kết nối một hồ sơ để bắt đầu hành trình." :
                profile.DisplayName + "   /   $" + profile.Credits.ToString("N0") + "   /   CẤP " + (profile.LevelIndex + 1) + "   /   " +
                (profile.RealmKind == "offline" ? "HỒ SƠ LAN · TÁCH BIỆT ONLINE" : "HỒ SƠ " + profile.RealmKind.ToUpperInvariant());
            endpointLabel.text = "MÁY CHỦ  " + session.Endpoint;
            status.text = session.Busy ? "ĐANG XỬ LÝ · Chờ máy chủ xác nhận…" : !string.IsNullOrEmpty(session.ErrorCode) ? ErrorText(session.ErrorCode) : SuccessText(session.Notice);
            status.EnableInClassList("error-text", !string.IsNullOrEmpty(session.ErrorCode));
            bool garage = selectedTab == "garage" && profile != null;
            root.EnableInClassList("career-garage-mode", garage);
            bool hasFeedback = session.Busy || !string.IsNullOrEmpty(session.ErrorCode) ||
                (!string.IsNullOrEmpty(session.Notice) && session.Notice != "view");
            footer.EnableInClassList("career-footer-feedback", hasFeedback);
            retry.style.display = session.CanRetry ? DisplayStyle.Flex : DisplayStyle.None;
            refresh.SetEnabled(!session.Busy && session.HasCredential && !guest);
            tabs.SetEnabled(!session.Busy); close.SetEnabled(!session.Busy); confirm.SetEnabled(!session.Busy);
            foreach (var button in tabButtons) button.EnableInClassList("is-selected", button.name == "career-tab-" + selectedTab);
            // Preserve typed fields while a request is in flight. A completed response rebuilds from server state.
            if (session.Busy) { body.SetEnabled(false); return; }
            body.SetEnabled(true);
            CaptureScroll();
            string focusedName = (surface.panel?.focusController.focusedElement as VisualElement)?.name;
            body.Clear(); password = recovery = exportText = null;
            renderedTab = selectedTab; RenderBody(profile);
            if (scrollByTab.TryGetValue(selectedTab, out var offset))
                body.schedule.Execute(() => { var scroll = body.Q<ScrollView>(); if (IsOpen && scroll != null) scroll.scrollOffset = offset; });
            if (!string.IsNullOrEmpty(focusedName) && focusedName != "career-password" && focusedName != "career-recovery")
                body.schedule.Execute(() => { if (IsOpen) body.Q(focusedName)?.Focus(); });
        }
        private void CaptureScroll()
        {
            var scroll = body?.Q<ScrollView>();
            if (scroll != null && !string.IsNullOrEmpty(renderedTab)) scrollByTab[renderedTab] = scroll.scrollOffset;
        }
        private void RenderBody(CareerProfileReadModel profile)
        {
            bool preview = selectedTab == "garage" || selectedTab == "shop" || selectedTab == "characters";
            root.EnableInClassList("career-preview-mode", preview && profile != null);
            PreviewVisibilityChanged?.Invoke(preview && profile != null);
            if (selectedTab == "account") { Account(); return; }
            if (selectedTab == "characters") { Characters(profile); return; }
            if (profile == null)
            {
                body.Add(Text("MỖI HÀNH TRÌNH CẦN MỘT HỒ SƠ.", "career-section-title"));
                body.Add(Text("Hồ sơ được lưu trên máy chủ đang chọn. Khách mới và chế độ tập offline không tích lũy vào garage này.", "description"));
                body.Add(Button("KẾT NỐI HỒ SƠ", () => { Close(); ConnectRequested?.Invoke(); }, "primary"));
                body.Add(Button("ĐĂNG NHẬP TÀI KHOẢN", () => { selectedTab = "account"; Render(); }, "secondary")); return;
            }
            if (selectedTab == "garage") Garage(profile);
            else if (selectedTab == "shop") Shop(profile);
            else if (selectedTab == "campaign") Campaign(profile);
            else Ledger();
        }
        private void Garage(CareerProfileReadModel profile)
        {
            var garage = new VisualElement { name = "career-garage" }; garage.AddToClassList("career-garage"); body.Add(garage);
            var rail = new VisualElement { name = "career-garage-rail" }; rail.AddToClassList("career-garage-rail"); garage.Add(rail);
            rail.Add(Text("XE CỦA BẠN", "career-garage-heading"));
            var inventory = new ScrollView(ScrollViewMode.Vertical) { name = "career-bike-list", horizontalScrollerVisibility = ScrollerVisibility.Hidden };
            inventory.AddToClassList("career-garage-inventory"); rail.Add(inventory);
            BikeDefinition inspected = null;
            foreach (var bike in BikeCatalog.All)
            {
                if (!Owns(profile, bike.Id)) continue;
                if (inspected == null || (bike.Id == profile.SelectedBikeId && string.IsNullOrEmpty(inspectedBikeId)) || bike.Id == inspectedBikeId) inspected = bike;
            }
            if (inspected == null) { rail.Add(Text("Garage chưa có xe.", "description")); return; }
            inspectedBikeId = inspected.Id;
            SelectedBikePreviewRequested?.Invoke(inspected.CatalogIndex);
            foreach (var bike in BikeCatalog.All)
            {
                if (!Owns(profile, bike.Id)) continue;
                var definition = bike;
                var select = Button("", () => { inspectedBikeId = definition.Id; Render(); }, "career-garage-bike");
                select.name = "career-inspect-" + bike.Id;
                select.tooltip = "Xem trước " + bike.DisplayName;
                select.EnableInClassList("is-selected", inspected.Id == bike.Id);
                Sprite thumbnail = bikeThumbnails != null && bike.CatalogIndex < bikeThumbnails.Length ? bikeThumbnails[bike.CatalogIndex] : null;
                var image = new Image { name = "career-thumbnail-" + bike.Id, sprite = thumbnail, scaleMode = ScaleMode.ScaleToFit, pickingMode = PickingMode.Ignore };
                image.AddToClassList("career-garage-thumbnail");
                image.EnableInClassList("thumbnail-pending", thumbnail == null);
                if (thumbnail == null) image.tooltip = "Ảnh xe đang chờ bản render 3D được kiểm tra.";
                select.Add(image);
                var label = new VisualElement { pickingMode = PickingMode.Ignore }; label.AddToClassList("career-garage-bike-label");
                label.Add(Text(bike.DisplayName.ToUpperInvariant(), "career-garage-bike-name"));
                label.Add(Text(bike.Id == profile.SelectedBikeId ? "ĐANG DÙNG" : "ĐÃ SỞ HỮU", "career-garage-bike-state"));
                select.Add(label); inventory.Add(select);
            }
            rail.Add(new VisualElement { name = "career-garage-divider" });
            rail.Add(Text(inspected.DisplayName.ToUpperInvariant(), "career-garage-title"));
            int condition = 0;
            foreach (var owned in profile.Bikes) if (owned.BikeId == inspected.Id) condition = owned.Condition;
            var conditionLabel = Row("career-garage-condition-label");
            conditionLabel.Add(Text("TÌNH TRẠNG XE", "career-garage-condition-name"));
            conditionLabel.Add(Text(condition.ToString(CultureInfo.InvariantCulture) + "%", "career-garage-condition-value")); rail.Add(conditionLabel);
            var conditionTrack = new VisualElement { name = "career-garage-condition-track" };
            var conditionFill = new VisualElement { name = "career-garage-condition-fill" };
            conditionFill.style.width = Length.Percent(condition); conditionTrack.Add(conditionFill); rail.Add(conditionTrack);
            rail.Add(Text("Chọn xe để xem trước. Thay đổi xe dùng\nkhi máy chủ xác nhận.", "career-garage-help"));
            if (inRoom || guest) rail.Add(Text(inRoom ? "Rời phòng trước khi đổi hoặc sửa xe." : "Phiên khách không thực hiện giao dịch hồ sơ.", "hint amber"));
            var actionRail = Row("career-garage-actions"); garage.Add(actionRail);
            bool equipped = profile.SelectedBikeId == inspected.Id;
            var equip = Button(equipped ? "ĐANG DÙNG" : "CHỌN XE", () => CommandRequested?.Invoke(new CareerIntent("equip", inspected.Id)), "career-garage-action");
            equip.name = "career-equip"; equip.SetEnabled(!equipped && !inRoom && !guest && inspected.HasDistinctArt); actionRail.Add(equip);
            var separator = new VisualElement(); separator.AddToClassList("career-garage-action-divider"); actionRail.Add(separator);
            var repair = Button(condition == 100 ? "XE NGUYÊN VẸN" : "SỬA XE · $" + inspected.RepairCredits.ToString("N0"),
                () => Confirm("Sửa " + inspected.DisplayName + " về 100% với $" + inspected.RepairCredits.ToString("N0") + "?", "repair", inspected.Id), "career-garage-action");
            repair.name = "career-repair"; repair.SetEnabled(condition < 100 && profile.Credits >= inspected.RepairCredits && !inRoom && !guest); actionRail.Add(repair);
            bool allWrecked = profile.Bikes.Count > 0; int cheapestRepair = int.MaxValue;
            foreach (var owned in profile.Bikes)
            {
                allWrecked &= owned.Condition == 0;
                if (BikeCatalog.TryGet(owned.BikeId, out var definition)) cheapestRepair = Math.Min(cheapestRepair, definition.RepairCredits);
            }
            if (allWrecked && profile.Credits < cheapestRepair)
            {
                rail.Add(Text("HÀNH TRÌNH ĐÃ DỪNG · Xe hỏng và quỹ không đủ sửa.", "hint amber"));
                var restart = Button("BẮT ĐẦU LẠI HÀNH TRÌNH", () => Confirm("Bắt đầu lại từ đầu? Xe và chiến dịch hiện tại sẽ mất. Spark 450 trở về nguyên vẹn, quỹ $0. Tài khoản và lịch sử giao dịch được giữ lại.", "restartCareer"), "secondary");
                restart.SetEnabled(!inRoom && !guest); rail.Add(restart);
            }
        }
        private void Shop(CareerProfileReadModel profile) => BikeBrowser(profile, true);
        private void BikeBrowser(CareerProfileReadModel profile, bool shop)
        {
            body.Add(Text(shop ? "TÌM MỘT CẤU HÌNH PHÙ HỢP." : "XE CỦA BẠN.", "career-section-title"));
            body.Add(Text("Chọn một mẫu để so sánh với xe đang dùng. Giá, quyền sở hữu và tình trạng do máy chủ xác nhận.", "hint"));
            var layout = Row("career-showroom"); body.Add(layout);
            var list = new ScrollView(ScrollViewMode.Vertical) { name = "career-bike-list" };
            list.AddToClassList("career-scroll"); list.AddToClassList("career-bike-list"); layout.Add(list);
            BikeDefinition inspected = null;
            foreach (var bike in BikeCatalog.All)
            {
                if (!shop && !Owns(profile, bike.Id)) continue;
                if (inspected == null || bike.Id == inspectedBikeId) inspected = bike;
            }
            if (inspected == null) { layout.Add(Text("Garage chưa có xe.", "description")); return; }
            inspectedBikeId = inspected.Id;
            SelectedBikePreviewRequested?.Invoke(inspected.CatalogIndex);
            foreach (var bike in BikeCatalog.All)
            {
                bool owned = Owns(profile, bike.Id); if (!shop && !owned) continue;
                var definition = bike;
                var select = Button((bike.CatalogIndex + 1).ToString("00") + "   " + bike.DisplayName + "\n" +
                    (owned ? "ĐÃ SỞ HỮU" : !bike.HasDistinctArt ? "CHƯA MỞ" : "$" + bike.PriceCredits.ToString("N0")) +
                    (bike.Id == profile.SelectedBikeId ? " · ĐANG DÙNG" : ""), () =>
                    { inspectedBikeId = definition.Id; Render(); }, "career-bike-select");
                select.name = "career-inspect-" + bike.Id; select.EnableInClassList("is-selected", inspected.Id == bike.Id); list.Add(select);
            }
            var panel = new ScrollView(ScrollViewMode.Vertical) { name = "career-bike-detail" };
            panel.AddToClassList("career-bike-detail"); layout.Add(panel);
            panel.Add(Text(inspected.DisplayName.ToUpperInvariant(), "career-showroom-title"));
            bool isOwned = Owns(profile, inspected.Id), equipped = profile.SelectedBikeId == inspected.Id;
            int condition = 100; bool selectedRoadworthy = false;
            foreach (var bike in profile.Bikes)
            {
                if (bike.BikeId == inspected.Id) condition = bike.Condition;
                if (bike.BikeId == profile.SelectedBikeId) selectedRoadworthy = bike.Condition > 0;
            }
            panel.Add(Text(isOwned ? "TÌNH TRẠNG " + condition + "%" + (equipped ? " · ĐANG DÙNG" : " · ĐÃ SỞ HỮU") : "$" + inspected.PriceCredits.ToString("N0") + " · " + (inspected.HasDistinctArt ? "CÓ THỂ MUA" : "CHƯA MỞ"), "eyebrow amber"));
            panel.Add(Text(BikeStats(inspected), "career-bike-stats"));
            if (BikeCatalog.TryGet(profile.SelectedBikeId, out var current))
            {
                float difference = (inspected.Handling.MaximumSpeedMillimetersPerSecond - current.Handling.MaximumSpeedMillimetersPerSecond) * .0036f;
                panel.Add(Text("SO VỚI " + current.DisplayName.ToUpperInvariant() + "\nGiới hạn tốc độ " + difference.ToString("+0.#;-0.#;0", CultureInfo.InvariantCulture) + " km/h\nHệ số 1× lấy Spark 450 làm mốc. Đây là thông số thiết kế trong game.", "description"));
            }
            var selectedDefinition = inspected;
            panel.Add(PreviewButton(selectedDefinition));
            if (isOwned)
            {
                var equip = Button(equipped ? "ĐANG DÙNG" : "CHỌN XE", () => CommandRequested?.Invoke(new CareerIntent("equip", selectedDefinition.Id)), "primary");
                equip.SetEnabled(!equipped && !inRoom && !guest && inspected.HasDistinctArt); panel.Add(equip);
                var repair = Button("SỬA XE · $" + inspected.RepairCredits.ToString("N0"), () => Confirm("Sửa " + selectedDefinition.DisplayName + " về 100% với $" + selectedDefinition.RepairCredits.ToString("N0") + "?", "repair", selectedDefinition.Id), "secondary");
                repair.SetEnabled(condition < 100 && profile.Credits >= inspected.RepairCredits && !inRoom && !guest); panel.Add(repair);
            }
            else
            {
                var buy = Button("MUA THÊM · $" + inspected.PriceCredits.ToString("N0"), () => Confirm("Mua " + selectedDefinition.DisplayName + " với $" + selectedDefinition.PriceCredits.ToString("N0") + "?", "buy", selectedDefinition.Id), "primary");
                buy.SetEnabled(!inRoom && !guest && inspected.HasDistinctArt && profile.Credits >= inspected.PriceCredits); panel.Add(buy);
                int tradeValue = current == null ? 0 : current.TradeInCredits;
                var trade = Button("ĐỔI XE", () => Confirm("Bán chiếc đang dùng với $" + tradeValue.ToString("N0") + " và mua " + selectedDefinition.DisplayName + " với $" + selectedDefinition.PriceCredits.ToString("N0") + "?", "trade", selectedDefinition.Id), "secondary");
                trade.SetEnabled(!inRoom && !guest && inspected.HasDistinctArt && selectedRoadworthy && (long)profile.Credits + tradeValue >= inspected.PriceCredits); panel.Add(trade);
            }
            if (inRoom || guest) panel.Add(Text(inRoom ? "Rời phòng trước khi đổi, mua hoặc sửa xe." : "Phiên khách không thực hiện giao dịch hồ sơ.", "hint amber"));
        }
        private Button PreviewButton(BikeDefinition bike)
        {
            var button = Button("XEM 3D", () =>
            {
                if (session.Busy || !bike.HasDistinctArt) return;
                Close();
                if (!IsOpen) ShowcaseRequested?.Invoke(bike.CatalogIndex);
            }, "secondary");
            button.name = "career-preview-" + bike.Id;
            button.tooltip = "Xem thiết kế " + bike.DisplayName + " và trở lại hồ sơ.";
            button.SetEnabled(bike.HasDistinctArt);
            return button;
        }
        private static string BikeStats(BikeDefinition bike)
        {
            var tuning = bike.Handling;
            return "GIỚI HẠN " + (tuning.MaximumSpeedMillimetersPerSecond * .0036).ToString("0.#", CultureInfo.InvariantCulture) + " km/h" +
                "  ·  TĂNG TỐC ×" + (tuning.EnginePermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture) +
                "\nPHANH " + (tuning.BrakeDeceleration / 1000.0).ToString("0.#", CultureInfo.InvariantCulture) + " m/s²" +
                "  ·  BÁM CUA ×" + (tuning.CorneringPermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture);
        }
        private void Characters(CareerProfileReadModel profile)
        {
            body.Add(Text("CHỌN GƯƠNG MẶT CỦA HÀNH TRÌNH.", "career-section-title"));
            body.Add(Text("8 tay đua, mỗi người một phong cách. Lựa chọn thay đổi diện mạo; sức mạnh và phần thưởng giữ nguyên.", "hint"));
            bool hasStates = ContentRegistry.Actors != null && ContentRegistry.Actors.Portraits != null && ContentRegistry.Actors.Portraits.Length >= CharacterCatalog.Count * 3;
            if (hasStates)
            {
                var preview = new DropdownField("XEM BIỂU CẢM", new List<string> { "Bình thường", "Vui vẻ", "Tập trung" }, portraitState) { name = "career-portrait-state" };
                preview.AddToClassList("career-portrait-state");
                preview.RegisterValueChangedCallback(_ =>
                {
                    portraitState = preview.index; Render();
                    root.schedule.Execute(() => { if (IsOpen && selectedTab == "characters") root.Q<DropdownField>("career-portrait-state")?.Focus(); });
                });
                body.Add(preview);
            }
            var scroll = Scroll();
            var grid = Row("career-character-grid");
            scroll.Add(grid);
            foreach (var character in CharacterCatalog.All)
            {
                bool selected = profile != null && profile.SelectedCharacterId == character.Id;
                if (string.IsNullOrEmpty(inspectedCharacterId) && selected) inspectedCharacterId = character.Id;
                if (character.Id == inspectedCharacterId) SelectedCharacterPreviewRequested?.Invoke(character.CatalogIndex);
                bool available = ProductionContent.CharacterArtAvailable(character.CatalogIndex);
                var card = new VisualElement(); card.AddToClassList("career-character-card"); card.EnableInClassList("is-selected", selected);
                var portrait = CharacterPortrait(character.CatalogIndex, portraitState);
                if (portrait != null)
                {
                    var image = new Image { sprite = portrait, scaleMode = ScaleMode.ScaleToFit };
                    image.name = "career-portrait-" + character.Id; image.AddToClassList("career-character-portrait"); card.Add(image);
                }
                else
                {
                    var identity = Text(character.DisplayName, "career-character-portrait career-character-fallback");
                    identity.tooltip = "Ảnh chân dung sẽ xuất hiện khi nội dung được tải."; card.Add(identity);
                }
                card.Add(Text(character.DisplayName, "career-bike-name"));
                card.Add(Text(selected ? "ĐANG ĐỒNG HÀNH" : available ? "SẴN SÀNG LÊN ĐƯỜNG" : "CHƯA MỞ", "hint"));
                var definition = character;
                var choose = Button(selected ? "ĐANG CHỌN" : "CHỌN TAY ĐUA", () => SelectCharacter(definition), "secondary");
                choose.name = "career-character-" + character.Id;
                choose.SetEnabled(available && !selected && profile != null && !guest && !inRoom && !session.Busy);
                var inspect = Button("XEM TAY ĐUA", () => { inspectedCharacterId = definition.Id; SelectedCharacterPreviewRequested?.Invoke(definition.CatalogIndex); }, "secondary");
                inspect.SetEnabled(available); card.Add(inspect); card.Add(choose); grid.Add(card);
            }
            if (inRoom) body.Add(Text("Rời phòng hiện tại trước khi đổi tay đua cho hồ sơ.", "hint amber"));
            else if (guest || profile == null) body.Add(Text("Kết nối hồ sơ đã lưu để chọn tay đua cho hành trình. Chế độ luyện tập cho phép thử mọi tay đua đã mở.", "hint amber"));
        }
        private static Sprite CharacterPortrait(int index, int state)
        {
            var portraits = ContentRegistry.Actors == null ? null : ContentRegistry.Actors.Portraits;
            if (portraits == null) return null;
            int portraitIndex = portraits.Length >= CharacterCatalog.Count * 3 ? index * 3 + Mathf.Clamp(state, 0, 2) : index;
            return portraitIndex >= 0 && portraitIndex < portraits.Length ? portraits[portraitIndex] : null;
        }
        private void SelectCharacter(CharacterDefinition character)
        {
            if (session.Busy || session.Profile == null || guest || inRoom || !ProductionContent.CharacterArtAvailable(character.CatalogIndex)) return;
            if (session.Profile.SelectedCharacterId == character.Id) return;
            CommandRequested?.Invoke(new CareerIntent("character", characterId: character.Id));
        }
        private void Campaign(CareerProfileReadModel profile)
        {
            body.Add(Text("5 CẤP. 25 CHẶNG.", "career-section-title"));
            body.Add(Text("Top 3 ở đủ 5 tuyến để lên cấp. Chọn một chặng thuộc cấp hiện tại; kết quả luyện tập không cộng vào hồ sơ máy chủ.", "hint"));
            var list = Scroll();
            for (int level = 0; level < CampaignCatalog.LevelCount; level++)
            {
                int selectedLevel = level;
                var row = Row("career-campaign-row"); row.Add(Text("CẤP " + (level + 1).ToString("00"), "career-level"));
                foreach (var route in CampaignCatalog.Routes)
                {
                    int course = route.CourseIndex;
                    bool qualified = level < profile.LevelIndex || (level == profile.LevelIndex && (profile.QualificationMask & (1 << course)) != 0);
                    string state = !route.IsPlayable ? "SẮP RA MẮT" : level > profile.LevelIndex ? "CHƯA MỞ" : qualified ? "ĐÃ QUA" : "ĐUA";
                    var button = Button(route.DisplayName + "\n" + state, () => { Close(); RaceRequested?.Invoke(selectedLevel, course); }, "career-route");
                    button.SetEnabled(route.IsPlayable && level == profile.LevelIndex && !inRoom && !guest); button.EnableInClassList("qualified", qualified);
                    row.Add(button);
                }
                list.Add(row);
            }
            if (inRoom) body.Add(Text("Rời phòng hiện tại trước khi tạo chặng của hành trình.", "hint amber"));
            else if (profile.CampaignComplete) body.Add(Text("ĐÃ HOÀN THÀNH HÀNH TRÌNH · Bạn có thể đua lại cấp hiện tại hoặc luyện tập tự do.", "hint amber"));
        }
        private void Ledger()
        {
            body.Add(Text("LỊCH SỬ GIAO DỊCH", "career-section-title"));
            body.Add(Text("Số dư và phần thưởng chỉ thay đổi sau khi máy chủ ghi nhận thành công.", "hint"));
            var list = Scroll();
            if (session.Ledger.Count == 0) list.Add(Text("Chưa có giao dịch.", "description"));
            foreach (var entry in session.Ledger)
            {
                var row = Row("career-ledger-row"); var detail = new VisualElement(); detail.AddToClassList("career-grow");
                detail.Add(Text(Reason(entry.Reason), "career-bike-name")); detail.Add(Text(FormatTimestamp(entry.CreatedUtc), "hint")); row.Add(detail);
                row.Add(Text((entry.Delta >= 0 ? "+" : "-") + "$" + Math.Abs((long)entry.Delta).ToString("N0"), entry.Delta < 0 ? "career-amount error-text" : "career-amount amber"));
                row.Add(Text("SỐ DƯ $" + entry.Balance.ToString("N0"), "hint")); list.Add(row);
            }
        }
        private void Account()
        {
            var scroll = Scroll(); var profile = session.Profile;
            scroll.Add(Text("GIỮ LẠI HÀNH TRÌNH CỦA BẠN.", "career-section-title"));
            scroll.Add(Text("Tài khoản thuộc máy chủ này. Đăng nhập, đăng ký và đổi mật khẩu cần HTTPS. Mã khôi phục dùng một lần thay cho email; hãy tự lưu ở nơi riêng tư.", "description"));
            if (!string.IsNullOrEmpty(session.RecoveryCode))
            {
                scroll.Add(Text("LƯU MÃ KHÔI PHỤC MỚI · Chỉ hiển thị trong lần này", "eyebrow amber"));
                var code = Field(scroll, "MÃ KHÔI PHỤC", false); code.isReadOnly = true; code.value = session.RecoveryCode;
            }
            if (profile != null && !string.IsNullOrEmpty(profile.Username))
                scroll.Add(Text("ĐANG ĐĂNG NHẬP: " + profile.Username, "career-bike-name"));
            var username = Field(scroll, "TÊN TÀI KHOẢN", false); username.name = "career-username"; username.maxLength = 32;
            username.SetValueWithoutNotify(accountUsername);
            username.RegisterValueChangedCallback(e => accountUsername = e.newValue);
            password = Field(scroll, "MẬT KHẨU (HOẶC MẬT KHẨU MỚI KHI KHÔI PHỤC)", true); password.name = "career-password"; password.maxLength = 128;
            recovery = Field(scroll, "MÃ KHÔI PHỤC (CHỈ CẦN KHI QUÊN MẬT KHẨU)", true); recovery.name = "career-recovery"; recovery.maxLength = 256;
            var auth = Row("career-actions");
            auth.Add(Button("ĐĂNG NHẬP", () => SubmitAccount("login", username.value), "primary"));
            var register = Button("NÂNG CẤP HỒ SƠ", () => SubmitAccount("register", username.value), "secondary");
            register.SetEnabled(profile != null && string.IsNullOrEmpty(profile.Username)); auth.Add(register);
            auth.Add(Button("ĐỔI MẬT KHẨU BẰNG MÃ", () => SubmitAccount("recover", username.value), "secondary")); scroll.Add(auth);
            scroll.Add(Text("Dán mật khẩu và mã được hỗ trợ. Đăng nhập sẽ kết thúc phiên đang mở trước khi đổi hồ sơ.", "hint"));
            if (profile == null)
            {
                scroll.Add(Button("KẾT NỐI HỒ SƠ ĐỂ ĐĂNG KÝ", () => { Close(); ConnectRequested?.Invoke(); }, "secondary"));
                if(session.HasCredential&&(session.ErrorCode=="unauthorized"||session.ErrorCode=="auth_required"))
                {
                    scroll.Add(Text("Khóa hồ sơ đang lưu đã hết hạn hoặc bị thu hồi. Tài khoản đã đăng ký vẫn có thể đăng nhập hoặc khôi phục ở trên.","hint"));
                    scroll.Add(Button("BỎ KHÓA HỒ SƠ ĐÃ HẾT HẠN",()=>Confirm("Bỏ khóa cũ trên máy này? Bạn sẽ không còn truy cập hồ sơ vô danh cũ bằng khóa này. Nếu đã nâng cấp tài khoản, hãy đăng nhập hoặc khôi phục tài khoản để giữ tiến trình; bản sao lưu máy chủ vẫn cần cơ chế khôi phục của chủ máy. Sau khi bỏ khóa, KẾT NỐI HỒ SƠ sẽ tạo hồ sơ mới.","forget"),"secondary"));
                }
                return;
            }
            var logout = Row("career-actions");
            logout.Add(Button("ĐĂNG XUẤT MÁY NÀY", () => Confirm("Thu hồi khóa hồ sơ trên máy này và kết thúc phiên hiện tại?", "logout"), "secondary"));
            if (!string.IsNullOrEmpty(profile.Username)) logout.Add(Button("THU HỒI TẤT CẢ PHIÊN", () => Confirm("Đăng xuất tất cả phiên của tài khoản? Bạn cần đăng nhập lại trên từng máy.", "logoutAll"), "secondary"));
            scroll.Add(logout);
            if (!string.IsNullOrEmpty(profile.Username))
                scroll.Add(Button("TẠO MÃ KHÔI PHỤC MỚI", () => SubmitAccount("rotateRecovery", username.value), "secondary"));
            if (profile.RealmKind != "offline") { scroll.Add(Text("Sao lưu bằng văn bản chỉ dành cho hồ sơ LAN offline; dữ liệu online được quản lý trên máy chủ.", "hint")); return; }
            scroll.Add(Text("SAO LƯU LAN OFFLINE", "career-section-title"));
            scroll.Add(Text("Bản lưu chỉ nhập lại vào hồ sơ offline này và phải qua kiểm tra máy chủ. Nội dung bản lưu có dữ liệu cá nhân; chỉ dán hoặc lưu ở nơi bạn tin cậy.", "hint"));
            exportText = Field(scroll, "NỘI DUNG BẢN LƯU", false); exportText.multiline = true; exportText.maxLength = 131072; exportText.AddToClassList("career-save-text");
            exportText.value = session.ExportJson;
            var save = Row("career-actions"); save.Add(Button("XUẤT BẢN LƯU", () => CommandRequested?.Invoke(new CareerIntent("export")), "secondary"));
            save.Add(Button("NHẬP BẢN LƯU", () =>
            {
                pendingConfirmation = new CareerIntent("import", saveJson: exportText.value);
                confirmationText.text = "Nhập bản lưu này? Máy chủ sẽ kiểm tra nguồn và tính hợp lệ trước khi thay thế tiến trình offline.";
                confirmation.style.display = DisplayStyle.Flex; confirm.Focus();
            }, "secondary")); scroll.Add(save);
        }
        private void SubmitAccount(string operation, string username)
        {
            var command = new CareerIntent(operation, username: username.Trim(), password: password.value, recoveryCode: recovery.value);
            ClearSecrets(); CommandRequested?.Invoke(command);
        }
        private void ClearSecrets() { password?.SetValueWithoutNotify(""); recovery?.SetValueWithoutNotify(""); exportText?.SetValueWithoutNotify(""); }
        private void Confirm(string prompt, string operation, string bikeId = "")
        { pendingConfirmation = new CareerIntent(operation, bikeId); confirmationText.text = prompt; confirmation.style.display = DisplayStyle.Flex; confirm.Focus(); }
        private void HideConfirmation() { pendingConfirmation = null; if (confirmation != null) confirmation.style.display = DisplayStyle.None; }
        private ScrollView Scroll() { var scroll = new ScrollView(ScrollViewMode.Vertical); scroll.AddToClassList("career-scroll"); body.Add(scroll); return scroll; }
        private static bool Owns(CareerProfileReadModel profile, string id) { foreach (var bike in profile.Bikes) if (bike.BikeId == id) return true; return false; }
        private static VisualElement Row(string className) { var element = new VisualElement(); element.AddToClassList(className); return element; }
        private static Label Text(string value, string classes) { var label = new Label(value) { enableRichText = false }; foreach (var css in classes.Split(' ')) label.AddToClassList(css); return label; }
        private static Button Button(string label, Action action, string className) { var button = new Button(action) { text = label }; button.AddToClassList(className); return button; }
        private static TextField Field(VisualElement parent, string label, bool secret)
        { parent.Add(Text(label, "eyebrow")); var field = new TextField { isPasswordField = secret }; field.AddToClassList("endpoint"); parent.Add(field); return field; }
        private static string SuccessText(string operation)
        {
            switch (operation) { case "buy": return "Đã thêm xe vào garage."; case "trade": return "Đã đổi xe."; case "repair": return "Xe đã được sửa về 100%.";
                case "equip": return "Đã chọn xe cho chặng tới."; case "character": return "Đã chọn tay đua cho hành trình."; case "register": return "Đã nâng cấp hồ sơ. Hãy lưu mã khôi phục."; case "login": return "Đăng nhập thành công.";
                case "rotateRecovery": return "Đã tạo mã khôi phục mới. Mã cũ hết hiệu lực; hãy lưu mã mới."; case "recover": return "Đã đổi mật khẩu. Hãy lưu mã khôi phục mới."; case "logout": case "logoutAll": return "Đã thu hồi phiên và đăng xuất.";
                case "forget": return "Đã bỏ khóa cũ trên máy này. Chọn KẾT NỐI HỒ SƠ để tạo hồ sơ mới, hoặc đăng nhập tài khoản.";
                case "restartCareer": return "Hành trình đã bắt đầu lại: Spark 450 nguyên vẹn, quỹ $0.";
                case "import": return "Đã nhập bản lưu được máy chủ xác nhận."; case "export": return "Bản lưu đã sẵn sàng. Chọn toàn bộ nội dung để sao chép."; default: return "Tiến trình được máy chủ xác nhận. Có thể làm mới để cập nhật."; }
        }
        private static string Reason(string reason)
        {
            switch (reason) { case "buy": return "Mua xe"; case "trade": return "Đổi xe"; case "repair": return "Sửa xe"; case "race": case "race_result": return "Kết quả cuộc đua"; case "restartCareer": case "career_restart": return "Bắt đầu lại hành trình"; case "opening": case "starting_credits": return "Quỹ khởi đầu"; default: return reason; }
        }
        private static string FormatTimestamp(string value)
        {
            return DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var timestamp)
                ? timestamp.ToString("dd/MM/yyyy HH:mm 'UTC'", CultureInfo.InvariantCulture)
                : "Thời gian chưa rõ";
        }
        private static string ErrorText(string code)
        {
            switch (code)
            {
                case "unauthorized": case "auth_required": return "Hãy kết nối hồ sơ đã lưu hoặc đăng nhập tài khoản trước.";
                case "https_required": return "Đổi địa chỉ máy chủ sang wss:// để đăng nhập qua kết nối TLS.";
                case "network_unavailable": return "Không nhận được phản hồi. Kiểm tra kết nối; Thử lại giữ nguyên mã giao dịch.";
                case "invalid_username": return "Tên tài khoản cần 3–24 ký tự a–z, 0–9, dấu gạch dưới hoặc gạch nối.";
                case "weak_password": case "invalid_password": return "Mật khẩu cần 12–128 ký tự. Hãy dùng một mật khẩu dài và riêng cho tài khoản.";
                case "not_bankrupt": return "Hồ sơ vẫn còn xe chạy được hoặc đủ quỹ sửa xe. Làm mới garage để tiếp tục hành trình.";
                case "repair_required": return "Xe đang chọn đã hỏng. Sửa xe trước khi đổi hoặc đua.";
                case "invalid_save": return "Bản lưu không hợp lệ hoặc đã bị thay đổi. Dùng bản xuất nguyên vẹn từ máy chủ.";
                case "foreign_save": return "Bản lưu thuộc hồ sơ hoặc máy chủ khác; không thể nhập vào hồ sơ này.";
                case "stale_save": return "Bản lưu đã cũ. Xuất bản mới nhất để bảo toàn giao dịch hiện tại.";
                case "already_owned": return "Xe này đã có trong garage. Làm mới để chọn xe.";
                case "rate_limited": return "Thao tác quá nhanh. Đợi một lát rồi thực hiện lại.";
                case "insufficient_credits": return "Quỹ chưa đủ cho giao dịch này. Hãy hoàn thành thêm chặng đua.";
                case "invalid_credentials": case "login_failed": return "Tên tài khoản, mật khẩu hoặc mã khôi phục chưa đúng.";
                case "username_unavailable": case "username_taken": return "Tên tài khoản đã có người dùng. Hãy chọn tên khác.";
                case "profile_busy": case "in_match": case "in_room": return "Rời phòng đua rồi thực hiện giao dịch này.";
                case "storage_unavailable": return "Máy chủ chưa lưu được dữ liệu. Thử lại sau; số dư chưa được xác nhận thay đổi.";
                default: return "Chưa thực hiện được thao tác (" + code + "). Làm mới hồ sơ và kiểm tra dữ liệu vừa nhập.";
            }
        }
        private void OnDestroy()
        {
            if (session != null) session.Changed -= Render;
            ClearSecrets(); bindings.Dispose();
            foreach (var element in disabledBehind) element.SetEnabled(true);
            disabledBehind.Clear(); root?.RemoveFromHierarchy();
            surface?.RemoveFromClassList("career-is-open");
            CommandRequested = null; RefreshRequested = RetryRequested = ConnectRequested = Closed = null;
            RaceRequested = null; PreviewVisibilityChanged?.Invoke(false);
            ShowcaseRequested = SelectedBikePreviewRequested = SelectedCharacterPreviewRequested = null; PreviewVisibilityChanged = null;
        }
    }
}
