/**
 * notifications.js — WebSocket push notifications
 */
(function () {
  'use strict';

  if (typeof window === 'undefined') return;

  const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${wsScheme}://${window.location.host}/ws/notifications/`);

  const badge = document.querySelector('[data-notification-badge]') ||
                document.querySelector('.badge.bg-danger');

  socket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    if (data.type !== 'notification') return;

    // Update badge count
    if (badge) {
      const current = parseInt(badge.textContent || '0', 10);
      badge.textContent = current + 1;
      badge.classList.remove('d-none');
    }

    // Show browser toast (if permission granted)
    if (Notification && Notification.permission === 'granted') {
      new Notification(data.title, { body: data.message, icon: '/static/img/logo.svg' });
    }
  };

  socket.onopen = () => {
    // Request browser notification permission once
    if (Notification && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  };

  socket.onclose = () => console.warn('[WS] Notifications disconnected');
})();
