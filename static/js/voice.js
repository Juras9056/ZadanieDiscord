/**
 * voice.js — WebRTC voice chat using the VoiceConsumer WebSocket signaling server.
 * Supports listen-only mode when no microphone is available.
 */
(function () {
  'use strict';

  const joinBtn = document.getElementById('joinVoiceBtn');
  const leaveBtn = document.getElementById('leaveVoiceBtn');
  const muteBtn = document.getElementById('muteBtn');
  const statusText = document.getElementById('voiceStatusText');
  const micIcon = document.getElementById('micIcon');
  const participantsList = document.getElementById('participantsList');
  const remoteAudios = document.getElementById('remoteAudios');

  if (!joinBtn) return;

  let socket = null;
  let localStream = null;
  let muted = false;
  const peers = {};

  const ICE_SERVERS = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

  // ─── UI helpers ─────────────────────────────────────────────────────────

  function addParticipant(username) {
    if (document.getElementById('p-' + username)) return;
    const empty = document.getElementById('emptyMsg');
    if (empty) empty.remove();
    const badge = document.createElement('span');
    badge.id = 'p-' + username;
    badge.className = 'badge bg-secondary d-flex align-items-center gap-1 p-2';
    badge.innerHTML = `<i class="bi bi-mic-fill text-success" id="mic-${escHtml(username)}"></i>${escHtml(username)}`;
    participantsList.appendChild(badge);
  }

  function removeParticipant(username) {
    const el = document.getElementById('p-' + username);
    if (el) el.remove();
    if (!participantsList.querySelector('.badge')) {
      const em = document.createElement('span');
      em.className = 'text-muted small';
      em.id = 'emptyMsg';
      em.textContent = 'Brak uczestników';
      participantsList.appendChild(em);
    }
  }

  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // ─── WebRTC peer ─────────────────────────────────────────────────────────

  function createPeer(remoteUsername, initiate) {
    if (peers[remoteUsername]) return peers[remoteUsername];
    const pc = new RTCPeerConnection(ICE_SERVERS);
    peers[remoteUsername] = pc;

    if (localStream) localStream.getTracks().forEach(t => pc.addTrack(t, localStream));

    pc.ontrack = (event) => {
      let audio = document.getElementById('audio-' + remoteUsername);
      if (!audio) {
        audio = document.createElement('audio');
        audio.id = 'audio-' + remoteUsername;
        audio.autoplay = true;
        remoteAudios.appendChild(audio);
      }
      audio.srcObject = event.streams[0];
    };

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        socket.send(JSON.stringify({ type: 'ice', to: remoteUsername, candidate: event.candidate }));
      }
    };

    if (initiate) {
      pc.createOffer()
        .then(offer => pc.setLocalDescription(offer))
        .then(() => {
          socket.send(JSON.stringify({ type: 'offer', to: remoteUsername, sdp: pc.localDescription }));
        });
    }
    return pc;
  }

  // ─── WebSocket connection ────────────────────────────────────────────────

  function connectSocket(withMic) {
    const wsScheme = location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${wsScheme}://${location.host}/ws/voice/${VOICE_CHANNEL_ID}/`);

    socket.onopen = () => {
      statusText.textContent = withMic
        ? 'Połączono z kanałem głosowym'
        : 'Połączono (tryb nasłuchu — brak mikrofonu)';
      micIcon.className = withMic ? 'bi bi-mic-fill text-success' : 'bi bi-mic-mute text-warning';
      micIcon.style.fontSize = '3rem';
      joinBtn.classList.add('d-none');
      leaveBtn.classList.remove('d-none');
      if (withMic) muteBtn.classList.remove('d-none');
      addParticipant(CURRENT_USER);
    };

    socket.onclose = () => {
      statusText.textContent = 'Rozłączono';
      micIcon.className = 'bi bi-mic-mute text-muted';
      joinBtn.classList.remove('d-none');
      leaveBtn.classList.add('d-none');
      muteBtn.classList.add('d-none');
      Object.keys(peers).forEach(u => {
        peers[u].close();
        delete peers[u];
        const a = document.getElementById('audio-' + u);
        if (a) a.remove();
        removeParticipant(u);
      });
      removeParticipant(CURRENT_USER);
      if (localStream) { localStream.getTracks().forEach(t => t.stop()); localStream = null; }
    };

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'peer_joined') {
        addParticipant(data.username);
        if (data.username !== CURRENT_USER) createPeer(data.username, true);
      } else if (data.type === 'peer_left') {
        removeParticipant(data.username);
        if (peers[data.username]) {
          peers[data.username].close();
          delete peers[data.username];
          const a = document.getElementById('audio-' + data.username);
          if (a) a.remove();
        }
      } else if (data.type === 'offer') {
        const pc = createPeer(data.from, false);
        await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        socket.send(JSON.stringify({ type: 'answer', to: data.from, sdp: pc.localDescription }));
      } else if (data.type === 'answer') {
        const pc = peers[data.from];
        if (pc) await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
      } else if (data.type === 'ice') {
        const pc = peers[data.from];
        if (pc && data.candidate) await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
      }
    };
  }

  // ─── Join button ─────────────────────────────────────────────────────────

  joinBtn.addEventListener('click', async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      statusText.textContent = 'Brak obsługi mikrofonu — dołączasz w trybie nasłuchu.';
      micIcon.className = 'bi bi-mic-mute text-warning';
      connectSocket(false);
      return;
    }

    // Check if any audio input device is connected before calling getUserMedia
    let hasAudioInput = false;
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      hasAudioInput = devices.some(d => d.kind === 'audioinput');
    } catch (_) {}

    if (!hasAudioInput) {
      statusText.textContent = 'Nie wykryto mikrofonu. Dołączasz w trybie nasłuchu.';
      micIcon.className = 'bi bi-mic-mute text-warning';
      connectSocket(false);
      return;
    }

    try {
      localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      connectSocket(true);
    } catch (err) {
      const isPermission = err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError';
      statusText.textContent = isPermission
        ? 'Odmówiono dostępu do mikrofonu. Dołączasz w trybie nasłuchu.'
        : `Błąd mikrofonu (${err.name}). Dołączasz w trybie nasłuchu.`;
      micIcon.className = 'bi bi-mic-mute text-warning';
      connectSocket(false);
    }
  });

  leaveBtn.addEventListener('click', () => { if (socket) socket.close(); });

  muteBtn.addEventListener('click', () => {
    if (!localStream) return;
    muted = !muted;
    localStream.getAudioTracks().forEach(t => { t.enabled = !muted; });
    muteBtn.innerHTML = muted
      ? '<i class="bi bi-mic-mute-fill text-danger"></i>'
      : '<i class="bi bi-mic-fill"></i>';
    const micEl = document.getElementById('mic-' + CURRENT_USER);
    if (micEl) micEl.className = muted ? 'bi bi-mic-mute-fill text-danger' : 'bi bi-mic-fill text-success';
  });
})();
