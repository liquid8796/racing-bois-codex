mergeInto(LibraryManager.library, {
  $RBState: { socket: null, receiver: '' },
  RB_Connect__deps: ['$RBState'],
  RB_Connect: function (receiver, endpoint) {
    if (RBState.socket) { RBState.socket.close(); RBState.socket = null; }
    RBState.receiver = UTF8ToString(receiver);
    var current;
    try { current = new WebSocket(UTF8ToString(endpoint)); }
    catch (error) { SendMessage(RBState.receiver, 'OnSocketClosed', 'Invalid server address'); return; }
    RBState.socket = current;
    current.onopen = function () { if (RBState.socket === current) SendMessage(RBState.receiver, 'OnSocketOpened', ''); };
    current.onmessage = function (event) {
      if (RBState.socket !== current || typeof event.data !== 'string') return;
      if (event.data.length > 32768) {
        RBState.socket = null;
        current.close(1009, 'Message too large');
        SendMessage(RBState.receiver, 'OnSocketClosed', 'Message too large');
        return;
      }
      SendMessage(RBState.receiver, 'OnSocketMessage', event.data);
    };
    current.onclose = function (event) {
      if (RBState.socket === current) { RBState.socket = null; SendMessage(RBState.receiver, 'OnSocketClosed', event.reason ? String(event.reason).slice(0, 160) : String(event.code)); }
    };
    current.onerror = function () { if (RBState.socket === current) SendMessage(RBState.receiver, 'OnSocketClosed', 'Connection failed'); };
  },
  RB_Send__deps: ['$RBState'],
  RB_Send: function (text) {
    if (RBState.socket && RBState.socket.readyState === WebSocket.OPEN && RBState.socket.bufferedAmount < 65536)
      RBState.socket.send(UTF8ToString(text));
  },
  RB_Close__deps: ['$RBState'],
  RB_Close: function () { var previous = RBState.socket; RBState.socket = null; if (previous) previous.close(); },
  RB_Report: function (text) {
    var status = document.getElementById('network-status');
    if (status) {
      var value = JSON.parse(UTF8ToString(text));
      value.wasmHeapBytes = HEAPU8.buffer.byteLength;
      status.textContent = (value.mode === 'Local' ? 'Chơi đơn' : value.state === 'Connected' ? 'Đã kết nối' : 'Racing Bois') + ' · ' + value.peers + ' tay đua · ' + value.fps + ' fps';
      status.dataset.snapshot = JSON.stringify(value);
    }
  }
});
