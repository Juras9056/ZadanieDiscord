/**
 * main.js — General UI utilities
 */
(function () {
  'use strict';

  // Auto-dismiss alerts after 4s
  document.querySelectorAll('.alert.fade.show').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 4000);
  });
})();
