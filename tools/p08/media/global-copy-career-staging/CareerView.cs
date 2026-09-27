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
        private Button close, retry, refresh, confirm, cancel;
        private readonly List<Button> tabButtons = new List<Button>();
        private readonly List<VisualElement> disabledBehind = new List<VisualElement>();
        private VisualElement previousFocus;
        private CareerIntent pendingConfirmation;
        private Func<string> confirmationPrompt;
        private bool suppressGenericFocusRestore;
        private string locale = DisplayLanguage.Default;
        private static readonly string[] TabCaptionKeys =
        { "career.tabs.garage", "career.tabs.shop", "career.tabs.characters", "career.tabs.campaign", "career.tabs.ledger", "career.tabs.account" };
        private string selectedTab = "garage", renderedTab = "";
        private int portraitState;
        private int consumedBackFrame = -1;
        private bool inRoom, guest;
        private TextField password, recovery, exportText;
        public bool IsOpen => root != null && root.style.display.value != DisplayStyle.None;

        public void Initialize(UIDocument document, CareerSession application, string locale = null)
        {
            if (root != null) return;
            if (locale != null) this.locale = DisplayLanguage.Normalize(locale);
            session = application; surface = document.rootVisualElement.Q("surface");
            root = new VisualElement { name = "career", focusable = true }; root.AddToClassList("career-overlay");
            var header = Row("career-heading");
            header.Add(Text("RACING BOIS", "career-wordmark"));
            tabs = Row("career-tabs");
            AddTab("garage", T("career.tabs.garage")); AddTab("shop", T("career.tabs.shop")); AddTab("characters", T("career.tabs.characters")); AddTab("campaign", T("career.tabs.campaign"));
            AddTab("ledger", T("career.tabs.ledger")); AddTab("account", T("career.tabs.account")); header.Add(tabs);
            close = Button(T("common.done"), Close, "career-close"); close.name = "career-close"; header.Add(close); root.Add(header);
            summary = Text(T("career.summary.connectToSave"), "career-summary"); root.Add(summary);
            endpointLabel = Text("", "career-endpoint"); root.Add(endpointLabel);
            body = new VisualElement { name = "career-content" }; body.AddToClassList("career-body"); root.Add(body);
            confirmation = new VisualElement { name = "career-confirmation" }; confirmation.AddToClassList("career-confirmation");
            confirmationText = Text("", "description"); confirmation.Add(confirmationText);
            var confirmationActions = Row("career-actions");
            confirm = Button(T("common.confirm"), () => { var request = pendingConfirmation; HideConfirmation(); CommandRequested?.Invoke(request); }, "primary");
            confirmationActions.Add(confirm); cancel = Button(T("common.cancel"), HideConfirmation, "secondary"); confirmationActions.Add(cancel); confirmation.Add(confirmationActions); root.Add(confirmation);
            footer = Row("career-footer"); status = Text("", "career-status"); footer.Add(status);
            actions = Row("career-actions"); refresh = Button(T("common.refresh"), () => RefreshRequested?.Invoke(), "small-button");
            retry = Button(T("common.retry"), () => RetryRequested?.Invoke(), "small-button"); actions.Add(refresh); actions.Add(retry); footer.Add(actions); root.Add(footer);
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
            if (session.Busy) { status.text = T("career.status.awaitingConfirmation"); return; }
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
        public void SetLocale(string value)
        {
            string selected = DisplayLanguage.Normalize(value);
            if (locale == selected) return;
            locale = selected;
            if (root == null) return;
            // A language refresh is display-only: retain in-progress account input,
            // the selected tab/preview/scroll and the original confirmation intent.
            string passwordValue = password?.value, recoveryValue = recovery?.value, exportValue = exportText?.value;
            var focused = surface.panel?.focusController.focusedElement as VisualElement;
            bool passwordFocused = OwnsFocus(password, focused), recoveryFocused = OwnsFocus(recovery, focused),
                exportFocused = OwnsFocus(exportText, focused);
            // UI Toolkit may focus a field's internal text-input child. Avoid the
            // generic name lookup selecting a different field's identical child name.
            suppressGenericFocusRestore = passwordFocused || recoveryFocused || exportFocused;
            try { RefreshLocalizedChrome(); Render(); }
            finally { suppressGenericFocusRestore = false; }
            if (passwordValue != null && password != null) password.SetValueWithoutNotify(passwordValue);
            if (recoveryValue != null && recovery != null) recovery.SetValueWithoutNotify(recoveryValue);
            if (exportValue != null && exportText != null) exportText.SetValueWithoutNotify(exportValue);
            if (confirmationPrompt != null) confirmationText.text = confirmationPrompt();
            if (passwordFocused || recoveryFocused || exportFocused)
                root.schedule.Execute(() =>
                {
                    if (!IsOpen || selectedTab != "account") return;
                    if (passwordFocused) password?.Focus();
                    else if (recoveryFocused) recovery?.Focus();
                    else exportText?.Focus();
                });
        }
        private void RefreshLocalizedChrome()
        {
            for (int index = 0; index < tabButtons.Count; index++) tabButtons[index].text = T(TabCaptionKeys[index]);
            close.text = T("common.done"); confirm.text = T("common.confirm"); cancel.text = T("common.cancel");
            refresh.text = T("common.refresh"); retry.text = T("common.retry");
        }
        private static bool OwnsFocus(TextField field, VisualElement focused) =>
            field != null && focused != null && (ReferenceEquals(field, focused) || field.Contains(focused));
        private string T(string key) => UiText.Get(locale, key);
        private string F(string key, params UiTextArgument[] arguments) => UiText.Format(locale, key, arguments);
        private static UiTextArgument A(string name, string value) => new UiTextArgument(name, value);
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
            summary.text = profile == null ? T("career.summary.empty") : profile.RealmKind == "offline" ? F("career.summary.offline", A("player", profile.DisplayName), A("credits", profile.Credits.ToString("N0")), A("level", (profile.LevelIndex + 1).ToString())) : F("career.summary.realm", A("player", profile.DisplayName), A("credits", profile.Credits.ToString("N0")), A("level", (profile.LevelIndex + 1).ToString()), A("realm", profile.RealmKind.ToUpperInvariant()));
            endpointLabel.text = F("career.summary.endpoint", A("endpoint", session.Endpoint));
            status.text = session.Busy ? T("career.status.busy") : !string.IsNullOrEmpty(session.ErrorCode) ? ErrorText(session.ErrorCode) : SuccessText(session.Notice);
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
            if (!suppressGenericFocusRestore && !string.IsNullOrEmpty(focusedName) && focusedName != "career-password" && focusedName != "career-recovery")
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
                body.Add(Text(T("career.profile.requiredTitle"), "career-section-title"));
                body.Add(Text(T("career.profile.storageHint"), "description"));
                body.Add(Button(T("career.profile.connect"), () => { Close(); ConnectRequested?.Invoke(); }, "primary"));
                body.Add(Button(T("career.account.openLogin"), () => { selectedTab = "account"; Render(); }, "secondary")); return;
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
            rail.Add(Text(T("career.garage.ownedHeading"), "career-garage-heading"));
            var inventory = new ScrollView(ScrollViewMode.Vertical) { name = "career-bike-list", horizontalScrollerVisibility = ScrollerVisibility.Hidden };
            inventory.AddToClassList("career-garage-inventory"); rail.Add(inventory);
            BikeDefinition inspected = null;
            foreach (var bike in BikeCatalog.All)
            {
                if (!Owns(profile, bike.Id)) continue;
                if (inspected == null || (bike.Id == profile.SelectedBikeId && string.IsNullOrEmpty(inspectedBikeId)) || bike.Id == inspectedBikeId) inspected = bike;
            }
            if (inspected == null) { rail.Add(Text(T("career.garage.empty"), "description")); return; }
            inspectedBikeId = inspected.Id;
            SelectedBikePreviewRequested?.Invoke(inspected.CatalogIndex);
            foreach (var bike in BikeCatalog.All)
            {
                if (!Owns(profile, bike.Id)) continue;
                var definition = bike;
                var select = Button("", () => { inspectedBikeId = definition.Id; Render(); }, "career-garage-bike");
                select.name = "career-inspect-" + bike.Id;
                select.tooltip = F("career.garage.previewTooltip", A("bike", bike.DisplayName));
                select.EnableInClassList("is-selected", inspected.Id == bike.Id);
                Sprite thumbnail = bikeThumbnails != null && bike.CatalogIndex < bikeThumbnails.Length ? bikeThumbnails[bike.CatalogIndex] : null;
                var image = new Image { name = "career-thumbnail-" + bike.Id, sprite = thumbnail, scaleMode = ScaleMode.ScaleToFit, pickingMode = PickingMode.Ignore };
                image.AddToClassList("career-garage-thumbnail");
                image.EnableInClassList("thumbnail-pending", thumbnail == null);
                if (thumbnail == null) image.tooltip = T("career.garage.thumbnailPending");
                select.Add(image);
                var label = new VisualElement { pickingMode = PickingMode.Ignore }; label.AddToClassList("career-garage-bike-label");
                label.Add(Text(bike.DisplayName.ToUpperInvariant(), "career-garage-bike-name"));
                label.Add(Text(bike.Id == profile.SelectedBikeId ? T("career.bike.equipped") : T("career.bike.owned"), "career-garage-bike-state"));
                select.Add(label); inventory.Add(select);
            }
            rail.Add(new VisualElement { name = "career-garage-divider" });
            rail.Add(Text(inspected.DisplayName.ToUpperInvariant(), "career-garage-title"));
            int condition = 0;
            foreach (var owned in profile.Bikes) if (owned.BikeId == inspected.Id) condition = owned.Condition;
            var conditionLabel = Row("career-garage-condition-label");
            conditionLabel.Add(Text(T("career.garage.conditionHeading"), "career-garage-condition-name"));
            conditionLabel.Add(Text(condition.ToString(CultureInfo.InvariantCulture) + "%", "career-garage-condition-value")); rail.Add(conditionLabel);
            var conditionTrack = new VisualElement { name = "career-garage-condition-track" };
            var conditionFill = new VisualElement { name = "career-garage-condition-fill" };
            conditionFill.style.width = Length.Percent(condition); conditionTrack.Add(conditionFill); rail.Add(conditionTrack);
            rail.Add(Text(T("career.garage.previewHint"), "career-garage-help"));
            if (inRoom || guest) rail.Add(Text(inRoom ? T("career.garage.leaveRoom") : T("career.profile.guestTransactions"), "hint amber"));
            var actionRail = Row("career-garage-actions"); garage.Add(actionRail);
            bool equipped = profile.SelectedBikeId == inspected.Id;
            var equip = Button(equipped ? T("career.bike.equipped") : T("career.garage.equip"), () => CommandRequested?.Invoke(new CareerIntent("equip", inspected.Id)), "career-garage-action");
            equip.name = "career-equip"; equip.SetEnabled(!equipped && !inRoom && !guest && inspected.HasDistinctArt); actionRail.Add(equip);
            var separator = new VisualElement(); separator.AddToClassList("career-garage-action-divider"); actionRail.Add(separator);
            var repair = Button(condition == 100 ? T("career.garage.pristine") : F("career.garage.repairButton", A("cost", inspected.RepairCredits.ToString("N0"))),
                () => Confirm(() => F("career.garage.repairConfirm", A("bike", inspected.DisplayName), A("cost", inspected.RepairCredits.ToString("N0"))), "repair", inspected.Id), "career-garage-action");
            repair.name = "career-repair"; repair.SetEnabled(condition < 100 && profile.Credits >= inspected.RepairCredits && !inRoom && !guest); actionRail.Add(repair);
            bool allWrecked = profile.Bikes.Count > 0; int cheapestRepair = int.MaxValue;
            foreach (var owned in profile.Bikes)
            {
                allWrecked &= owned.Condition == 0;
                if (BikeCatalog.TryGet(owned.BikeId, out var definition)) cheapestRepair = Math.Min(cheapestRepair, definition.RepairCredits);
            }
            if (allWrecked && profile.Credits < cheapestRepair)
            {
                rail.Add(Text(T("career.garage.bankruptNotice"), "hint amber"));
                var restart = Button(T("career.garage.restart"), () => Confirm(() => T("career.garage.restartConfirm"), "restartCareer"), "secondary");
                restart.SetEnabled(!inRoom && !guest); rail.Add(restart);
            }
        }
        private void Shop(CareerProfileReadModel profile) => BikeBrowser(profile, true);
        private void BikeBrowser(CareerProfileReadModel profile, bool shop)
        {
            body.Add(Text(shop ? T("career.shop.heading") : T("career.garage.browserHeading"), "career-section-title"));
            body.Add(Text(T("career.shop.compareHint"), "hint"));
            var layout = Row("career-showroom"); body.Add(layout);
            var list = new ScrollView(ScrollViewMode.Vertical) { name = "career-bike-list" };
            list.AddToClassList("career-scroll"); list.AddToClassList("career-bike-list"); layout.Add(list);
            BikeDefinition inspected = null;
            foreach (var bike in BikeCatalog.All)
            {
                if (!shop && !Owns(profile, bike.Id)) continue;
                if (inspected == null || bike.Id == inspectedBikeId) inspected = bike;
            }
            if (inspected == null) { layout.Add(Text(T("career.garage.empty"), "description")); return; }
            inspectedBikeId = inspected.Id;
            SelectedBikePreviewRequested?.Invoke(inspected.CatalogIndex);
            foreach (var bike in BikeCatalog.All)
            {
                bool owned = Owns(profile, bike.Id); if (!shop && !owned) continue;
                var definition = bike;
                var select = Button(owned ? (bike.Id == profile.SelectedBikeId ? F("career.bikeList.ownedEquipped", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName)) : F("career.bikeList.owned", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName))) : !bike.HasDistinctArt ? (bike.Id == profile.SelectedBikeId ? F("career.bikeList.lockedEquipped", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName)) : F("career.bikeList.locked", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName))) : (bike.Id == profile.SelectedBikeId ? F("career.bikeList.priceEquipped", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName), A("cost", bike.PriceCredits.ToString("N0"))) : F("career.bikeList.price", A("index", (bike.CatalogIndex + 1).ToString("00")), A("bike", bike.DisplayName), A("cost", bike.PriceCredits.ToString("N0")))), () =>
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
            panel.Add(Text(isOwned ? (equipped ? F("career.bikeDetail.equipped", A("condition", condition.ToString())) : F("career.bikeDetail.owned", A("condition", condition.ToString()))) : (inspected.HasDistinctArt ? F("career.bikeDetail.available", A("cost", inspected.PriceCredits.ToString("N0"))) : F("career.bikeDetail.locked", A("cost", inspected.PriceCredits.ToString("N0")))), "eyebrow amber"));
            panel.Add(Text(BikeStats(inspected), "career-bike-stats"));
            if (BikeCatalog.TryGet(profile.SelectedBikeId, out var current))
            {
                float difference = (inspected.Handling.MaximumSpeedMillimetersPerSecond - current.Handling.MaximumSpeedMillimetersPerSecond) * .0036f;
                panel.Add(Text(F("career.bike.compare", A("bike", current.DisplayName.ToUpperInvariant()), A("difference", difference.ToString("+0.#;-0.#;0", CultureInfo.InvariantCulture))), "description"));
            }
            var selectedDefinition = inspected;
            panel.Add(PreviewButton(selectedDefinition));
            if (isOwned)
            {
                var equip = Button(equipped ? T("career.bike.equipped") : T("career.garage.equip"), () => CommandRequested?.Invoke(new CareerIntent("equip", selectedDefinition.Id)), "primary");
                equip.SetEnabled(!equipped && !inRoom && !guest && inspected.HasDistinctArt); panel.Add(equip);
                var repair = Button(F("career.garage.repairButton", A("cost", inspected.RepairCredits.ToString("N0"))), () => Confirm(() => F("career.garage.repairConfirm", A("bike", selectedDefinition.DisplayName), A("cost", selectedDefinition.RepairCredits.ToString("N0"))), "repair", selectedDefinition.Id), "secondary");
                repair.SetEnabled(condition < 100 && profile.Credits >= inspected.RepairCredits && !inRoom && !guest); panel.Add(repair);
            }
            else
            {
                var buy = Button(F("career.shop.buyButton", A("cost", inspected.PriceCredits.ToString("N0"))), () => Confirm(() => F("career.shop.buyConfirm", A("bike", selectedDefinition.DisplayName), A("cost", selectedDefinition.PriceCredits.ToString("N0"))), "buy", selectedDefinition.Id), "primary");
                buy.SetEnabled(!inRoom && !guest && inspected.HasDistinctArt && profile.Credits >= inspected.PriceCredits); panel.Add(buy);
                int tradeValue = current == null ? 0 : current.TradeInCredits;
                var trade = Button(T("career.shop.trade"), () => Confirm(() => F("career.shop.tradeConfirm", A("tradeValue", tradeValue.ToString("N0")), A("bike", selectedDefinition.DisplayName), A("cost", selectedDefinition.PriceCredits.ToString("N0"))), "trade", selectedDefinition.Id), "secondary");
                trade.SetEnabled(!inRoom && !guest && inspected.HasDistinctArt && selectedRoadworthy && (long)profile.Credits + tradeValue >= inspected.PriceCredits); panel.Add(trade);
            }
            if (inRoom || guest) panel.Add(Text(inRoom ? T("career.shop.leaveRoom") : T("career.profile.guestTransactions"), "hint amber"));
        }
        private Button PreviewButton(BikeDefinition bike)
        {
            var button = Button(T("career.bike.preview"), () =>
            {
                if (session.Busy || !bike.HasDistinctArt) return;
                Close();
                if (!IsOpen) ShowcaseRequested?.Invoke(bike.CatalogIndex);
            }, "secondary");
            button.name = "career-preview-" + bike.Id;
            button.tooltip = F("career.bike.previewTooltip", A("bike", bike.DisplayName));
            button.SetEnabled(bike.HasDistinctArt);
            return button;
        }
        private string BikeStats(BikeDefinition bike)
        {
            var tuning = bike.Handling;
            return F("career.bike.stats", A("speed", (tuning.MaximumSpeedMillimetersPerSecond * .0036).ToString("0.#", CultureInfo.InvariantCulture)), A("acceleration", (tuning.EnginePermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture)), A("braking", (tuning.BrakeDeceleration / 1000.0).ToString("0.#", CultureInfo.InvariantCulture)), A("cornering", (tuning.CorneringPermille / 1000.0).ToString("0.00", CultureInfo.InvariantCulture)));
        }
        private void Characters(CareerProfileReadModel profile)
        {
            body.Add(Text(T("career.characters.heading"), "career-section-title"));
            body.Add(Text(T("career.characters.selectionHint"), "hint"));
            bool hasStates = ContentRegistry.Actors != null && ContentRegistry.Actors.Portraits != null && ContentRegistry.Actors.Portraits.Length >= CharacterCatalog.Count * 3;
            if (hasStates)
            {
                var preview = new DropdownField(T("career.characters.expressionLabel"), new List<string> { T("career.characters.expressionNeutral"), T("career.characters.expressionHappy"), T("career.characters.expressionFocused") }, portraitState) { name = "career-portrait-state" };
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
                    identity.tooltip = T("career.characters.portraitPending"); card.Add(identity);
                }
                card.Add(Text(character.DisplayName, "career-bike-name"));
                card.Add(Text(selected ? T("career.characters.accompanying") : available ? T("career.characters.ready") : T("career.state.locked"), "hint"));
                var definition = character;
                var choose = Button(selected ? T("career.characters.selected") : T("career.characters.choose"), () => SelectCharacter(definition), "secondary");
                choose.name = "career-character-" + character.Id;
                choose.SetEnabled(available && !selected && profile != null && !guest && !inRoom && !session.Busy);
                var inspect = Button(T("career.characters.inspect"), () => { inspectedCharacterId = definition.Id; SelectedCharacterPreviewRequested?.Invoke(definition.CatalogIndex); }, "secondary");
                inspect.SetEnabled(available); card.Add(inspect); card.Add(choose); grid.Add(card);
            }
            if (inRoom) body.Add(Text(T("career.characters.leaveRoom"), "hint amber"));
            else if (guest || profile == null) body.Add(Text(T("career.characters.connectProfile"), "hint amber"));
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
            body.Add(Text(T("career.campaign.heading"), "career-section-title"));
            body.Add(Text(T("career.campaign.progressionHint"), "hint"));
            var list = Scroll();
            for (int level = 0; level < CampaignCatalog.LevelCount; level++)
            {
                int selectedLevel = level;
                var row = Row("career-campaign-row"); row.Add(Text(F("career.campaign.level", A("level", (level + 1).ToString("00"))), "career-level"));
                foreach (var route in CampaignCatalog.Routes)
                {
                    int course = route.CourseIndex;
                    bool qualified = level < profile.LevelIndex || (level == profile.LevelIndex && (profile.QualificationMask & (1 << course)) != 0);
                    string state = !route.IsPlayable ? T("career.campaign.comingSoon") : level > profile.LevelIndex ? T("career.state.locked") : qualified ? T("career.campaign.qualified") : T("career.campaign.race");
                    var button = Button(route.DisplayName + "\n" + state, () => { Close(); RaceRequested?.Invoke(selectedLevel, course); }, "career-route");
                    button.SetEnabled(route.IsPlayable && level == profile.LevelIndex && !inRoom && !guest); button.EnableInClassList("qualified", qualified);
                    row.Add(button);
                }
                list.Add(row);
            }
            if (inRoom) body.Add(Text(T("career.campaign.leaveRoom"), "hint amber"));
            else if (profile.CampaignComplete) body.Add(Text(T("career.campaign.complete"), "hint amber"));
        }
        private void Ledger()
        {
            body.Add(Text(T("career.ledger.heading"), "career-section-title"));
            body.Add(Text(T("career.ledger.authorityHint"), "hint"));
            var list = Scroll();
            if (session.Ledger.Count == 0) list.Add(Text(T("career.ledger.empty"), "description"));
            foreach (var entry in session.Ledger)
            {
                var row = Row("career-ledger-row"); var detail = new VisualElement(); detail.AddToClassList("career-grow");
                detail.Add(Text(Reason(entry.Reason), "career-bike-name")); detail.Add(Text(FormatTimestamp(entry.CreatedUtc), "hint")); row.Add(detail);
                row.Add(Text((entry.Delta >= 0 ? "+" : "-") + "$" + Math.Abs((long)entry.Delta).ToString("N0"), entry.Delta < 0 ? "career-amount error-text" : "career-amount amber"));
                row.Add(Text(F("career.ledger.balance", A("balance", entry.Balance.ToString("N0"))), "hint")); list.Add(row);
            }
        }
        private void Account()
        {
            var scroll = Scroll(); var profile = session.Profile;
            scroll.Add(Text(T("career.account.heading"), "career-section-title"));
            scroll.Add(Text(T("career.account.securityHint"), "description"));
            if (!string.IsNullOrEmpty(session.RecoveryCode))
            {
                scroll.Add(Text(T("career.account.newRecoveryNotice"), "eyebrow amber"));
                var code = Field(scroll, T("career.account.recoveryCodeLabel"), false); code.isReadOnly = true; code.value = session.RecoveryCode;
            }
            if (profile != null && !string.IsNullOrEmpty(profile.Username))
                scroll.Add(Text(F("career.account.loggedIn", A("username", profile.Username)), "career-bike-name"));
            var username = Field(scroll, T("career.account.usernameLabel"), false); username.name = "career-username"; username.maxLength = 32;
            username.SetValueWithoutNotify(accountUsername);
            username.RegisterValueChangedCallback(e => accountUsername = e.newValue);
            password = Field(scroll, T("career.account.passwordLabel"), true); password.name = "career-password"; password.maxLength = 128;
            recovery = Field(scroll, T("career.account.recoveryInputLabel"), true); recovery.name = "career-recovery"; recovery.maxLength = 256;
            var auth = Row("career-actions");
            auth.Add(Button(T("career.account.login"), () => SubmitAccount("login", username.value), "primary"));
            var register = Button(T("career.account.register"), () => SubmitAccount("register", username.value), "secondary");
            register.SetEnabled(profile != null && string.IsNullOrEmpty(profile.Username)); auth.Add(register);
            auth.Add(Button(T("career.account.recover"), () => SubmitAccount("recover", username.value), "secondary")); scroll.Add(auth);
            scroll.Add(Text(T("career.account.pasteHint"), "hint"));
            if (profile == null)
            {
                scroll.Add(Button(T("career.account.connectToRegister"), () => { Close(); ConnectRequested?.Invoke(); }, "secondary"));
                if(session.HasCredential&&(session.ErrorCode=="unauthorized"||session.ErrorCode=="auth_required"))
                {
                    scroll.Add(Text(T("career.account.expiredCredentialHint"),"hint"));
                    scroll.Add(Button(T("career.account.forgetCredential"),()=>Confirm(() => T("career.account.forgetCredentialConfirm"),"forget"),"secondary"));
                }
                return;
            }
            var logout = Row("career-actions");
            logout.Add(Button(T("career.account.logout"), () => Confirm(() => T("career.account.logoutConfirm"), "logout"), "secondary"));
            if (!string.IsNullOrEmpty(profile.Username)) logout.Add(Button(T("career.account.logoutAll"), () => Confirm(() => T("career.account.logoutAllConfirm"), "logoutAll"), "secondary"));
            scroll.Add(logout);
            if (!string.IsNullOrEmpty(profile.Username))
                scroll.Add(Button(T("career.account.rotateRecovery"), () => SubmitAccount("rotateRecovery", username.value), "secondary"));
            if (profile.RealmKind != "offline") { scroll.Add(Text(T("career.backup.onlineRestriction"), "hint")); return; }
            scroll.Add(Text(T("career.backup.heading"), "career-section-title"));
            scroll.Add(Text(T("career.backup.privacyHint"), "hint"));
            exportText = Field(scroll, T("career.backup.contentLabel"), false); exportText.multiline = true; exportText.maxLength = 131072; exportText.AddToClassList("career-save-text");
            exportText.value = session.ExportJson;
            var save = Row("career-actions"); save.Add(Button(T("career.backup.export"), () => CommandRequested?.Invoke(new CareerIntent("export")), "secondary"));
            save.Add(Button(T("career.backup.import"), () =>
            {
                pendingConfirmation = new CareerIntent("import", saveJson: exportText.value);
                confirmationPrompt = () => T("career.backup.importConfirm"); confirmationText.text = confirmationPrompt();
                confirmation.style.display = DisplayStyle.Flex; confirm.Focus();
            }, "secondary")); scroll.Add(save);
        }
        private void SubmitAccount(string operation, string username)
        {
            var command = new CareerIntent(operation, username: username.Trim(), password: password.value, recoveryCode: recovery.value);
            ClearSecrets(); CommandRequested?.Invoke(command);
        }
        private void ClearSecrets() { password?.SetValueWithoutNotify(""); recovery?.SetValueWithoutNotify(""); exportText?.SetValueWithoutNotify(""); }
        private void Confirm(Func<string> prompt, string operation, string bikeId = "")
        { pendingConfirmation = new CareerIntent(operation, bikeId); confirmationPrompt = prompt; confirmationText.text = prompt(); confirmation.style.display = DisplayStyle.Flex; confirm.Focus(); }
        private void HideConfirmation() { pendingConfirmation = null; confirmationPrompt = null; if (confirmation != null) confirmation.style.display = DisplayStyle.None; }
        private ScrollView Scroll() { var scroll = new ScrollView(ScrollViewMode.Vertical); scroll.AddToClassList("career-scroll"); body.Add(scroll); return scroll; }
        private static bool Owns(CareerProfileReadModel profile, string id) { foreach (var bike in profile.Bikes) if (bike.BikeId == id) return true; return false; }
        private static VisualElement Row(string className) { var element = new VisualElement(); element.AddToClassList(className); return element; }
        private static Label Text(string value, string classes) { var label = new Label(value) { enableRichText = false }; foreach (var css in classes.Split(' ')) label.AddToClassList(css); return label; }
        private static Button Button(string label, Action action, string className) { var button = new Button(action) { text = label }; button.AddToClassList(className); return button; }
        private static TextField Field(VisualElement parent, string label, bool secret)
        { parent.Add(Text(label, "eyebrow")); var field = new TextField { isPasswordField = secret }; field.AddToClassList("endpoint"); parent.Add(field); return field; }
        private string SuccessText(string operation)
        {
            switch (operation) { case "buy": return T("career.notice.buy"); case "trade": return T("career.notice.trade"); case "repair": return T("career.notice.repair");
                case "equip": return T("career.notice.equip"); case "character": return T("career.notice.character"); case "register": return T("career.notice.register"); case "login": return T("career.notice.login");
                case "rotateRecovery": return T("career.notice.rotateRecovery"); case "recover": return T("career.notice.recover"); case "logout": case "logoutAll": return T("career.notice.logout");
                case "forget": return T("career.notice.forget");
                case "restartCareer": return T("career.notice.restart");
                case "import": return T("career.notice.import"); case "export": return T("career.notice.export"); default: return T("career.notice.default"); }
        }
        private string Reason(string reason)
        {
            switch (reason) { case "buy": return T("career.ledger.reasonBuy"); case "trade": return T("career.ledger.reasonTrade"); case "repair": return T("career.ledger.reasonRepair"); case "race": case "race_result": return T("career.ledger.reasonRace"); case "restartCareer": case "career_restart": return T("career.ledger.reasonRestart"); case "opening": case "starting_credits": return T("career.ledger.reasonOpening"); default: return reason; }
        }
        private string FormatTimestamp(string value)
        {
            return DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var timestamp) ? timestamp.ToString("dd/MM/yyyy HH:mm 'UTC'", CultureInfo.InvariantCulture) : T("career.ledger.unknownTime");
        }
        private string ErrorText(string code)
        {
            switch (code)
            {
                case "unauthorized": case "auth_required": return T("career.error.authRequired");
                case "https_required": return T("career.error.httpsRequired");
                case "network_unavailable": return T("career.error.networkUnavailable");
                case "invalid_username": return T("career.error.invalidUsername");
                case "weak_password": case "invalid_password": return T("career.error.invalidPassword");
                case "not_bankrupt": return T("career.error.notBankrupt");
                case "repair_required": return T("career.error.repairRequired");
                case "invalid_save": return T("career.error.invalidSave");
                case "foreign_save": return T("career.error.foreignSave");
                case "stale_save": return T("career.error.staleSave");
                case "already_owned": return T("career.error.alreadyOwned");
                case "rate_limited": return T("career.error.rateLimited");
                case "insufficient_credits": return T("career.error.insufficientCredits");
                case "invalid_credentials": case "login_failed": return T("career.error.invalidCredentials");
                case "username_unavailable": case "username_taken": return T("career.error.usernameUnavailable");
                case "profile_busy": case "in_match": case "in_room": return T("career.error.profileBusy");
                case "storage_unavailable": return T("career.error.storageUnavailable");
                default: return F("career.error.unknown", A("code", code));
            }
        }
        private void OnDestroy()
        {
            if (session != null) session.Changed -= Render;
            ClearSecrets(); confirmationPrompt = null; bindings.Dispose();
            foreach (var element in disabledBehind) element.SetEnabled(true);
            disabledBehind.Clear(); root?.RemoveFromHierarchy();
            surface?.RemoveFromClassList("career-is-open");
            CommandRequested = null; RefreshRequested = RetryRequested = ConnectRequested = Closed = null;
            RaceRequested = null; PreviewVisibilityChanged?.Invoke(false);
            ShowcaseRequested = SelectedBikePreviewRequested = SelectedCharacterPreviewRequested = null; PreviewVisibilityChanged = null;
        }
    }
}
