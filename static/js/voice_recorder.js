/**
 * voice_recorder.js — Record audio messages using MediaRecorder API
 */
(function () {
  'use strict';

  const voiceBtn = document.getElementById('voiceBtn');
  const recordingStatus = document.getElementById('recordingStatus');
  if (!voiceBtn) return;

  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;

  voiceBtn.addEventListener('click', async function () {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

        mediaRecorder.onstop = async function () {
          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const file = new File([blob], `voice_${Date.now()}.webm`, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append('file', file);
          try {
            const res = await fetch(
              typeof UPLOAD_URL !== 'undefined' ? UPLOAD_URL : '/chat/upload/',
              {
                method: 'POST',
                headers: { 'X-CSRFToken': typeof CSRF_TOKEN !== 'undefined' ? CSRF_TOKEN : '' },
                body: formData,
              }
            );
            const data = await res.json();
            if (data.url) {
              const uploadPreview = document.getElementById('uploadPreview');
              if (uploadPreview) {
                uploadPreview.innerHTML = `<audio controls class="mt-1"><source src="${data.url}"></audio>`;
              }
            }
          } catch (err) {
            console.error('Voice upload error:', err);
          }
          // Stop all tracks
          stream.getTracks().forEach(t => t.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        voiceBtn.classList.add('btn-danger');
        voiceBtn.classList.remove('btn-outline-secondary');
        voiceBtn.innerHTML = '<i class="bi bi-stop-fill"></i>';
        if (recordingStatus) recordingStatus.classList.remove('d-none');
      } catch (err) {
        alert('Nie można uzyskać dostępu do mikrofonu: ' + err.message);
      }
    } else {
      mediaRecorder.stop();
      isRecording = false;
      voiceBtn.classList.remove('btn-danger');
      voiceBtn.classList.add('btn-outline-secondary');
      voiceBtn.innerHTML = '<i class="bi bi-mic"></i>';
      if (recordingStatus) recordingStatus.classList.add('d-none');
    }
  });
})();
