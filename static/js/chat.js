/**
 * chat.js — WebSocket client for channel chat and DM
 */
(function () {
  'use strict';

  const messagesContainer = document.getElementById('messagesContainer');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');

  if (!messagesContainer) return;

  // Scroll to bottom on load
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  // ─── Channel WebSocket ───────────────────────────────────────────────────
  let socket = null;

  if (typeof CHANNEL_ID !== 'undefined') {
    const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${wsScheme}://${window.location.host}/ws/chat/${CHANNEL_ID}/`);

    socket.onopen = () => console.log('[WS] Channel connected');
    socket.onclose = () => console.warn('[WS] Channel disconnected');

    socket.onmessage = function (event) {
      const data = JSON.parse(event.data);
      if (data.type === 'chat_message') appendMessage(data);
    };
  }

  // ─── DM WebSocket ────────────────────────────────────────────────────────
  if (typeof OTHER_USER !== 'undefined') {
    const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${wsScheme}://${window.location.host}/ws/dm/${OTHER_USER}/`);

    socket.onopen = () => console.log('[WS] DM connected');
    socket.onclose = () => console.warn('[WS] DM disconnected');

    socket.onmessage = function (event) {
      const data = JSON.parse(event.data);
      if (data.type === 'dm_message') appendMessage(data);
    };
  }

  // ─── Send message ────────────────────────────────────────────────────────
  function sendMessage() {
    const content = messageInput.value.trim();
    if (!content || !socket) return;
    socket.send(JSON.stringify({ type: 'chat_message', content }));
    messageInput.value = '';
  }

  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
  if (messageInput) {
    messageInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // ─── Append incoming message to DOM ─────────────────────────────────────
  function appendMessage(data) {
    const isOwn = data.author === (typeof CURRENT_USER !== 'undefined' ? CURRENT_USER : '');
    const div = document.createElement('div');
    div.className = `message d-flex gap-3 mb-3${isOwn ? ' own-message' : ''}`;
    div.dataset.msgId = data.message_id || data.dm_id || '';
    div.innerHTML = `
      <img src="${data.avatar || '/static/img/default_avatar.png'}"
           class="rounded-circle flex-shrink-0" width="40" height="40" style="object-fit:cover" />
      <div>
        <div class="d-flex align-items-baseline gap-2">
          <span class="fw-semibold small">${escapeHtml(data.author)}</span>
          <span class="text-muted" style="font-size:.7rem">${data.timestamp}</span>
        </div>
        <p class="mb-1 small">${escapeHtml(data.content)}</p>
      </div>`;
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // ─── File upload ─────────────────────────────────────────────────────────
  const fileUpload = document.getElementById('fileUpload');
  const uploadPreview = document.getElementById('uploadPreview');

  if (fileUpload) {
    fileUpload.addEventListener('change', async function () {
      const file = this.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await fetch(UPLOAD_URL, {
          method: 'POST',
          headers: { 'X-CSRFToken': CSRF_TOKEN },
          body: formData,
        });
        const data = await res.json();
        if (data.url && uploadPreview) {
          if (data.type === 'image') {
            uploadPreview.innerHTML = `<img src="${data.url}" class="img-fluid rounded mt-1" style="max-width:200px" />`;
          } else {
            uploadPreview.innerHTML = `<a href="${data.url}" class="btn btn-sm btn-outline-secondary mt-1">Pobierz plik</a>`;
          }
        }
      } catch (err) {
        console.error('Upload error:', err);
      }
      this.value = '';
    });
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────
  function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }
})();
