mergeInto(LibraryManager.library, {
  $RBMusic: {
    audio: null, receiver: '', id: '', requested: false, unlocked: false,
    paused: false, hidden: false, gain: 0.18, muted: false, seek: 0,
    gesture: null, visibility: null, generation: 0,
    notify: function (state, code) {
      if (RBMusic.receiver) SendMessage(RBMusic.receiver, 'OnStreamEvent', JSON.stringify({ state: state, code: code || '', id: RBMusic.id }));
    },
    applyMix: function () {
      if (!RBMusic.audio) return;
      RBMusic.audio.muted = RBMusic.muted;
      RBMusic.audio.volume = Math.max(0, Math.min(1, RBMusic.gain));
    },
    tryPlay: function () {
      if (!RBMusic.audio || !RBMusic.requested || RBMusic.paused || RBMusic.hidden || !RBMusic.unlocked) return;
      var generation = RBMusic.generation;
      var result = RBMusic.audio.play();
      if (result && result.catch) result.catch(function (error) {
        if (generation !== RBMusic.generation) return;
        if (error && error.name === 'NotAllowedError') { RBMusic.unlocked = false; RBMusic.notify('gesture-required'); }
        else if (!error || error.name !== 'AbortError') RBMusic.notify('error', 'music-playback-failed');
      });
    },
    releaseSource: function () {
      RBMusic.generation++;
      RBMusic.requested = false;
      if (RBMusic.audio) { RBMusic.audio.pause(); RBMusic.audio.removeAttribute('src'); RBMusic.audio.load(); }
      RBMusic.id = ''; RBMusic.seek = 0;
    }
  },
  RB_MusicInitialize__deps: ['$RBMusic'],
  RB_MusicInitialize: function (receiver) {
    var owner = UTF8ToString(receiver);
    if (RBMusic.receiver && RBMusic.receiver !== owner) RBMusic.releaseSource();
    RBMusic.receiver = owner;
    if (RBMusic.audio) return;
    var audio = document.createElement('audio');
    audio.preload = 'metadata'; audio.setAttribute('playsinline', '');
    RBMusic.audio = audio; RBMusic.hidden = document.hidden;
    audio.addEventListener('playing', function () { if (RBMusic.requested) RBMusic.notify('playing'); });
    audio.addEventListener('waiting', function () { if (RBMusic.requested) RBMusic.notify('buffering'); });
    audio.addEventListener('ended', function () { if (RBMusic.requested) RBMusic.notify('ended'); });
    audio.addEventListener('error', function () { if (RBMusic.requested) RBMusic.notify('error', 'music-media-' + (audio.error ? audio.error.code : 0)); });
    audio.addEventListener('loadedmetadata', function () {
      if (RBMusic.seek > 0 && Number.isFinite(audio.duration)) audio.currentTime = Math.min(RBMusic.seek, Math.max(0, audio.duration - 0.01));
    });
    RBMusic.gesture = function (event) {
      if (!event.isTrusted) return;
      RBMusic.unlocked = true; RBMusic.tryPlay();
    };
    RBMusic.visibility = function () {
      RBMusic.hidden = document.hidden;
      if (RBMusic.hidden) { audio.pause(); if (RBMusic.requested) RBMusic.notify('paused'); }
      else RBMusic.tryPlay();
    };
    document.addEventListener('pointerdown', RBMusic.gesture, true);
    document.addEventListener('keydown', RBMusic.gesture, true);
    document.addEventListener('visibilitychange', RBMusic.visibility);
  },
  RB_MusicPlay__deps: ['$RBMusic'],
  RB_MusicPlay: function (id, url, loop, gain) {
    if (!RBMusic.audio) return 0;
    var nextId = UTF8ToString(id), raw = UTF8ToString(url), parsed;
    try { parsed = new URL(raw, location.href); } catch (_) { return 0; }
    var filename = parsed.pathname.split('/').pop();
    if (!/^[a-z0-9-]{1,64}$/.test(nextId) || raw.length > 2048 || raw.indexOf('%') >= 0 ||
        parsed.origin !== location.origin || !/^https?:$/.test(parsed.protocol) || parsed.username || parsed.password || parsed.search || parsed.hash ||
        parsed.pathname.indexOf('/Content/') !== 0 || !/[a-fA-F0-9]{64}\.ogg$/.test(filename)) return 0;
    RBMusic.releaseSource();
    RBMusic.id = nextId; RBMusic.requested = true; RBMusic.paused = false;
    RBMusic.gain = Number.isFinite(gain) ? gain : 0;
    RBMusic.audio.loop = !!loop; RBMusic.audio.src = parsed.href; RBMusic.applyMix(); RBMusic.audio.load();
    RBMusic.tryPlay();
    if (!RBMusic.unlocked) RBMusic.notify('gesture-required');
    return 1;
  },
  RB_MusicMix__deps: ['$RBMusic'],
  RB_MusicMix: function (muted, gain) { RBMusic.muted = !!muted; RBMusic.gain = Number.isFinite(gain) ? gain : 0; RBMusic.applyMix(); },
  RB_MusicPause__deps: ['$RBMusic'],
  RB_MusicPause: function (paused) { RBMusic.paused = !!paused; if (RBMusic.audio && RBMusic.paused) RBMusic.audio.pause(); else RBMusic.tryPlay(); },
  RB_MusicUnlock__deps: ['$RBMusic'],
  RB_MusicUnlock: function () {
    if (navigator.userActivation && !navigator.userActivation.isActive) return;
    RBMusic.unlocked = true; RBMusic.tryPlay();
  },
  RB_MusicStop__deps: ['$RBMusic'],
  RB_MusicStop: function () { RBMusic.releaseSource(); },
  RB_MusicPosition__deps: ['$RBMusic'],
  RB_MusicPosition: function () { return RBMusic.audio && Number.isFinite(RBMusic.audio.currentTime) ? RBMusic.audio.currentTime : 0; },
  RB_MusicSeek__deps: ['$RBMusic'],
  RB_MusicSeek: function (seconds) {
    RBMusic.seek = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
    if (RBMusic.audio && RBMusic.audio.readyState > 0 && Number.isFinite(RBMusic.audio.duration)) RBMusic.audio.currentTime = Math.min(RBMusic.seek, Math.max(0, RBMusic.audio.duration - 0.01));
  },
  RB_MusicDispose__deps: ['$RBMusic'],
  RB_MusicDispose: function (receiver) {
    if (RBMusic.receiver !== UTF8ToString(receiver)) return;
    RBMusic.releaseSource();
    if (RBMusic.gesture) { document.removeEventListener('pointerdown', RBMusic.gesture, true); document.removeEventListener('keydown', RBMusic.gesture, true); }
    if (RBMusic.visibility) document.removeEventListener('visibilitychange', RBMusic.visibility);
    RBMusic.audio = null; RBMusic.receiver = ''; RBMusic.gesture = null; RBMusic.visibility = null; RBMusic.unlocked = false;
  }
});
