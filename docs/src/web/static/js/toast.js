/**
 * Toast / Alert / Confirm — 统一通知系统（IIFE，挂 window.Toast）
 * 零外部依赖，纯 emoji 图标
 */
(function () {
  'use strict';

  let _container = null;
  let _loadingEl = null;

  function _ensureContainer() {
    if (!_container) {
      _container = document.createElement('div');
      _container.className = 'toast-container';
      document.body.appendChild(_container);
    }
    return _container;
  }

  /* ── Toast ───────────────────────────────────────────────── */
  function toast(msg, type, duration) {
    var c = _ensureContainer();
    var el = document.createElement('div');
    el.className = 'toast-item ' + type;
    el.textContent = (type === 'success' ? '✅ ' : '❌ ') + msg;
    c.appendChild(el);
    setTimeout(function () { el.remove(); }, duration || 2000);
  }

  function success(msg) { toast(msg, 'success', 1800); }
  function error(msg)   { toast(msg, 'error', 2500); }

  /* ── Alert ───────────────────────────────────────────────── */
  function alert(msg, title) {
    return new Promise(function (resolve) {
      _makePopup('💬', title || '提示', msg, [
        { text: '知道了', cls: 'btn-confirm', value: true }
      ], resolve);
    });
  }

  /* ── Confirm ─────────────────────────────────────────────── */
  function confirm(msg, title, danger) {
    return new Promise(function (resolve) {
      _makePopup('⚠️', title || '确认', msg, [
        { text: '取消', cls: 'btn-cancel', value: false },
        { text: '确定', cls: danger ? 'btn-danger' : 'btn-confirm', value: true }
      ], resolve);
    });
  }

  /* ── Loading ─────────────────────────────────────────────── */
  function showLoading(msg) {
    hideLoading();
    _loadingEl = document.createElement('div');
    _loadingEl.className = 'popup-overlay';
    _loadingEl.innerHTML =
      '<div class="popup-box" style="background:transparent;box-shadow:none;text-align:center;">' +
      '<div class="spinner" style="margin:0 auto 12px;border:3px solid rgba(255,255,255,.3);border-top-color:#fff;"></div>' +
      '<p style="color:#fff;font-size:15px;font-weight:500;">' + (msg || '处理中…') + '</p>' +
      '</div>';
    document.body.appendChild(_loadingEl);
  }

  function hideLoading() {
    if (_loadingEl) { _loadingEl.remove(); _loadingEl = null; }
  }

  /* ── 内部弹窗工厂 ────────────────────────────────────────── */
  function _makePopup(emoji, title, msg, buttons, resolve) {
    var overlay = document.createElement('div');
    overlay.className = 'popup-overlay';

    var btnHtml = buttons.map(function (b, i) {
      return '<button class="' + b.cls + '" data-idx="' + i + '">' + b.text + '</button>';
    }).join('');

    overlay.innerHTML =
      '<div class="popup-box">' +
      '<div style="font-size:44px;margin-bottom:8px;">' + emoji + '</div>' +
      '<h3>' + title + '</h3>' +
      '<p>' + msg + '</p>' +
      '<div class="popup-btns">' + btnHtml + '</div>' +
      '</div>';

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) resolve(false);
    });

    document.body.appendChild(overlay);

    var btns = overlay.querySelectorAll('button');
    btns.forEach(function (btn, i) {
      btn.addEventListener('click', function () {
        overlay.remove();
        resolve(buttons[i].value);
      });
    });
  }

  /* ── 导出 ────────────────────────────────────────────────── */
  window.Toast = {
    success: success,
    error: error,
    alert: alert,
    confirm: confirm,
    showLoading: showLoading,
    hideLoading: hideLoading,
  };
})();
