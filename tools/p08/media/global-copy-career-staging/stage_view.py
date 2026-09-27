"""Apply reviewed whole-expression edits and exact view-local locale wiring outside Assets."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
STAGE=Path(__file__).resolve().parent
bindings=json.loads((STAGE/'source-bindings.json').read_text(encoding='utf-8'))
source_path=ROOT/bindings['source']['path']
raw=source_path.read_bytes()
if hashlib.sha256(raw).hexdigest()!=bindings['source']['sha256']:
    raise RuntimeError('Reviewed Career source changed.')
source=raw.decode('utf-8-sig')

# A confirmation retains its display expression, independently of the immutable
# CareerIntent payload. Exact reviewed spans identify the prompt arguments.
confirmation_sites={16772,17713,22028,22483,22914,34768,35244,35447}
for site in sorted(bindings['sites'],key=lambda item:item['expressionStart'],reverse=True):
    start=site['expressionStart'];old=site['sourceExpression']
    if source[start:start+len(old)]!=old:
        raise RuntimeError('Whole expression changed at '+str(start))
    replacement=site['replacementExpression']
    if start in confirmation_sites:
        if source[start-8:start]!='Confirm(':
            raise RuntimeError('Reviewed confirmation argument moved.')
        replacement='() => '+replacement
    source=source[:start]+replacement+source[start+len(old):]

def edit_once(old,new):
    global source
    if source.count(old)!=1:
        raise RuntimeError('Expected one exact view integration anchor: '+old[:100])
    start=source.index(old)
    source=source[:start]+new+source[start+len(old):]

edit_once('private Button close, retry, refresh, confirm;', 'private Button close, retry, refresh, confirm, cancel;')
edit_once('private CareerIntent pendingConfirmation;', '''private CareerIntent pendingConfirmation;
        private Func<string> confirmationPrompt;
        private bool suppressGenericFocusRestore;
        private string locale = DisplayLanguage.Default;
        private static readonly string[] TabCaptionKeys =
        { "career.tabs.garage", "career.tabs.shop", "career.tabs.characters", "career.tabs.campaign", "career.tabs.ledger", "career.tabs.account" };''')
edit_once('public void Initialize(UIDocument document, CareerSession application)\r\n        {\r\n            if (root != null) return;',
    '''public void Initialize(UIDocument document, CareerSession application, string locale = null)
        {
            if (root != null) return;
            if (locale != null) this.locale = DisplayLanguage.Normalize(locale);''')
edit_once('confirmationActions.Add(confirm); confirmationActions.Add(Button(T("common.cancel"), HideConfirmation, "secondary"));',
    'confirmationActions.Add(confirm); cancel = Button(T("common.cancel"), HideConfirmation, "secondary"); confirmationActions.Add(cancel);')
edit_once('public void RefreshPresentation() => Render();', '''public void RefreshPresentation() => Render();
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
        private static UiTextArgument A(string name, string value) => new UiTextArgument(name, value);''')
for name in ['BikeStats','SuccessText','Reason','FormatTimestamp','ErrorText']:
    edit_once('private static string '+name+'(', 'private string '+name+'(')
edit_once('if (!string.IsNullOrEmpty(focusedName) && focusedName != "career-password" && focusedName != "career-recovery")',
    'if (!suppressGenericFocusRestore && !string.IsNullOrEmpty(focusedName) && focusedName != "career-password" && focusedName != "career-recovery")')
edit_once('confirmationText.text = T("career.backup.importConfirm");',
    'confirmationPrompt = () => T("career.backup.importConfirm"); confirmationText.text = confirmationPrompt();')
edit_once('private void Confirm(string prompt, string operation, string bikeId = "")\r\n        { pendingConfirmation = new CareerIntent(operation, bikeId); confirmationText.text = prompt; confirmation.style.display = DisplayStyle.Flex; confirm.Focus(); }',
    '''private void Confirm(Func<string> prompt, string operation, string bikeId = "")
        { pendingConfirmation = new CareerIntent(operation, bikeId); confirmationPrompt = prompt; confirmationText.text = prompt(); confirmation.style.display = DisplayStyle.Flex; confirm.Focus(); }''')
edit_once('private void HideConfirmation() { pendingConfirmation = null; if (confirmation != null) confirmation.style.display = DisplayStyle.None; }',
    'private void HideConfirmation() { pendingConfirmation = null; confirmationPrompt = null; if (confirmation != null) confirmation.style.display = DisplayStyle.None; }')
edit_once('ClearSecrets(); bindings.Dispose();', 'ClearSecrets(); confirmationPrompt = null; bindings.Dispose();')

# Preserve existing newline convention; the source syntax/callback structure outside
# reviewed spans and the named integration anchors is not rewritten.
source=source.replace('\r\n','\n').replace('\n','\r\n')
(STAGE/'CareerView.cs').write_bytes(source.encode('utf-8'))
(STAGE/'CareerView.cs.meta').write_bytes(source_path.with_suffix('.cs.meta').read_bytes())
print(json.dumps({'staged':'tools/p08/media/global-copy-career-staging/CareerView.cs',
    'sha256':hashlib.sha256((STAGE/'CareerView.cs').read_bytes()).hexdigest(),
    'wholeExpressionEdits':len(bindings['sites']),'confirmationPromptFactories':len(confirmation_sites)+1,
    'liveSourceUnchanged':hashlib.sha256(source_path.read_bytes()).hexdigest()==bindings['source']['sha256'],
    'scope':'Staged display-only locale wiring; no Assets writes or locale translations.'},indent=2))
