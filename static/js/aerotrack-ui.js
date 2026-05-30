/* =====================================================================
   AeroTrack Analytics — UI Utilities v2.0
   Vanilla JS only. No jQuery dependency.
   Exposes global: window.AT
   ===================================================================== */

(function (global) {
  'use strict';

  /* ─── Live clock ──────────────────────────────────────────────────── */
  function initClock() {
    var el = document.getElementById('at-clock');
    if (!el) return;

    function pad(n) { return n < 10 ? '0' + n : '' + n; }

    function tick() {
      var now = new Date();
      var h = pad(now.getHours());
      var m = pad(now.getMinutes());
      var s = pad(now.getSeconds());
      var day = now.toLocaleDateString('es-EC', { weekday: 'short', day: '2-digit', month: 'short' });
      el.textContent = day + ' · ' + h + ':' + m + ':' + s;
    }
    tick();
    setInterval(tick, 1000);
  }

  /* ─── Sidebar active state from URL ──────────────────────────────── */
  function highlightSidebarActive() {
    var path = global.location.pathname;
    var links = document.querySelectorAll('#sidebar .nav-item-link[href]');
    links.forEach(function (link) {
      var href = link.getAttribute('href');
      if (href && href !== '/' && path.startsWith(href)) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      } else {
        link.classList.remove('active');
        link.removeAttribute('aria-current');
      }
    });
  }

  /* ─── Toast notification system ──────────────────────────────────── */
  var TOAST_ICONS = {
    success: 'bi bi-check-circle-fill',
    error:   'bi bi-exclamation-circle-fill',
    warning: 'bi bi-exclamation-triangle-fill',
    info:    'bi bi-info-circle-fill'
  };

  function getToastContainer() {
    var c = document.getElementById('at-toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'at-toast-container';
      c.setAttribute('role', 'alert');
      c.setAttribute('aria-live', 'polite');
      c.setAttribute('aria-atomic', 'false');
      document.body.appendChild(c);
    }
    return c;
  }

  function toast(type, message, duration) {
    if (!type) type = 'info';
    if (!duration) duration = 4000;
    var container = getToastContainer();

    var el = document.createElement('div');
    el.className = 'at-toast ' + type;
    el.setAttribute('role', 'status');
    el.innerHTML =
      '<i class="at-toast-icon ' + (TOAST_ICONS[type] || TOAST_ICONS.info) + '" aria-hidden="true"></i>' +
      '<span class="at-toast-body">' + _escapeHtml(message) + '</span>' +
      '<button class="at-toast-close" type="button" aria-label="Cerrar notificación">' +
        '<i class="bi bi-x" aria-hidden="true"></i>' +
      '</button>';

    container.appendChild(el);

    /* Close button */
    el.querySelector('.at-toast-close').addEventListener('click', function () {
      dismissToast(el);
    });

    /* Auto-dismiss */
    var timer = setTimeout(function () { dismissToast(el); }, duration);

    /* Pause on hover */
    el.addEventListener('mouseenter', function () { clearTimeout(timer); });
    el.addEventListener('mouseleave', function () {
      timer = setTimeout(function () { dismissToast(el); }, 1500);
    });
  }

  function dismissToast(el) {
    if (!el || !el.parentNode) return;
    el.classList.add('leaving');
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 200);
  }

  function _escapeHtml(str) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
  }

  /* ─── Confirm modal ───────────────────────────────────────────────── */
  var _confirmResolve = null;

  function initConfirmModal() {
    var okBtn = document.getElementById('at-confirm-ok');
    if (!okBtn) return;
    okBtn.addEventListener('click', function () {
      var modal = bootstrap.Modal.getInstance(document.getElementById('at-confirm-modal'));
      if (modal) modal.hide();
      if (_confirmResolve) { _confirmResolve(true); _confirmResolve = null; }
    });
    document.getElementById('at-confirm-modal').addEventListener('hidden.bs.modal', function () {
      if (_confirmResolve) { _confirmResolve(false); _confirmResolve = null; }
    });
  }

  /* confirm(event, title, body) — call from onsubmit
     Returns false immediately to prevent submission, then submits
     programmatically after user confirmation.
     Usage: onsubmit="return AT.confirm(event, 'Eliminar registro', '¿Seguro?')" */
  function confirm(event, title, body) {
    event.preventDefault();
    var form = event.target;

    var titleEl = document.getElementById('at-confirm-title');
    var bodyEl  = document.getElementById('at-confirm-body');
    var okBtn   = document.getElementById('at-confirm-ok');
    if (titleEl) titleEl.childNodes[titleEl.childNodes.length - 1].textContent = title || 'Confirmar acción';
    if (bodyEl)  bodyEl.textContent = body  || '¿Estás seguro de que deseas continuar?';

    /* Style danger button red for destructive actions */
    if (okBtn) {
      if (title && (title.toLowerCase().includes('elimin') || title.toLowerCase().includes('borra') || title.toLowerCase().includes('desactiv'))) {
        okBtn.className = 'btn-at-danger';
        okBtn.textContent = 'Sí, continuar';
      } else {
        okBtn.className = 'btn-at-primary';
        okBtn.textContent = 'Confirmar';
      }
    }

    var modalEl = document.getElementById('at-confirm-modal');
    var bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    bsModal.show();

    _confirmResolve = function (confirmed) {
      if (confirmed) form.submit();
    };

    return false;
  }

  /* ─── Auto-refresh with visual countdown ─────────────────────────── */
  function startAutoRefresh(intervalSeconds, countdownSelector) {
    var remaining = intervalSeconds;
    var els = document.querySelectorAll(countdownSelector || '.at-refresh-countdown');

    function update() {
      els.forEach(function (el) { el.textContent = remaining; });
    }
    update();

    return setInterval(function () {
      remaining--;
      if (remaining <= 0) {
        global.location.reload();
        return;
      }
      update();
    }, 1000);
  }

  /* ─── Flash messages: auto-dismiss ───────────────────────────────── */
  function initFlashAutoDismiss() {
    var fb = document.getElementById('flash-bar');
    if (!fb) return;
    setTimeout(function () {
      fb.style.transition = 'opacity .4s';
      fb.style.opacity = '0';
      setTimeout(function () { if (fb.parentNode) fb.parentNode.removeChild(fb); }, 400);
    }, 4500);
  }

  /* ─── Bootstrap dropdown menu rounding fix ───────────────────────── */
  function initDropdownStyling() {
    document.querySelectorAll('.dropdown-menu').forEach(function (menu) {
      menu.style.borderRadius = menu.style.borderRadius || '12px';
    });
  }

  /* ─── Init ────────────────────────────────────────────────────────── */
  function init() {
    initClock();
    highlightSidebarActive();
    initConfirmModal();
    initFlashAutoDismiss();
    initDropdownStyling();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* ─── Public API ──────────────────────────────────────────────────── */
  global.AT = {
    toast:                toast,
    confirm:              confirm,
    startAutoRefresh:     startAutoRefresh,
    highlightSidebarActive: highlightSidebarActive,

    /* Convenience shorthands */
    success: function (msg, dur) { toast('success', msg, dur); },
    error:   function (msg, dur) { toast('error',   msg, dur); },
    warning: function (msg, dur) { toast('warning', msg, dur); },
    info:    function (msg, dur) { toast('info',    msg, dur); }
  };

}(window));
