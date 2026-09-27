mergeInto(LibraryManager.library, {
  $RBStorage: { receiver: '', installed: false },
  RB_StorageRead: function (key, persistent) {
    var value = '';
    try { value = (persistent ? localStorage : sessionStorage).getItem(UTF8ToString(key)) || ''; }
    catch (_) { return 0; }
    if (value.length > 8192) value = '';
    var pointer = _malloc(lengthBytesUTF8(value) + 1);
    stringToUTF8(value, pointer, lengthBytesUTF8(value) + 1);
    return pointer;
  },
  RB_StorageWrite: function (key, value, persistent) {
    try { (persistent ? localStorage : sessionStorage).setItem(UTF8ToString(key), UTF8ToString(value)); return 1; }
    catch (_) { return 0; }
  },
  RB_StorageRemove: function (key, persistent) {
    try { (persistent ? localStorage : sessionStorage).removeItem(UTF8ToString(key)); }
    catch (_) { }
  },
  RB_StorageFree: function (value) { _free(value); },
  RB_RegisterLifecycle__deps: ['$RBStorage'],
  RB_RegisterLifecycle: function (receiver) {
    RBStorage.receiver = UTF8ToString(receiver);
    if (RBStorage.installed) return;
    RBStorage.installed = true;
    document.addEventListener('visibilitychange', function () {
      if (RBStorage.receiver) SendMessage(RBStorage.receiver, 'OnPageVisibility', document.hidden ? 'hidden' : 'visible');
    });
  }
});
