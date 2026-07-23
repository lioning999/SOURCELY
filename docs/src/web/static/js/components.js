/**
 * 通用组件库
 * 弹框统一入口: showError / showSuccess / showConfirm，底层收归 _createPopup()
 * 登录态: initUserState
 */
import { getToken } from './api/core.js';

// ═══════════════════════════════════════════════════════════════
// 登录态（跨页面共用）
// ═══════════════════════════════════════════════════════════════

/**
 * 初始化用户状态显示。v3.0 按次付费，不再展示用户级配额。
 * @param {HTMLElement} quotaEl — 状态显示元素
 */
async function initUserState(quotaEl) {
  if (!quotaEl) return;
  const loggedIn = !!getToken();
  if (!loggedIn) { quotaEl.textContent = ''; return; }
  // v3.0 按次付费，不展示用户级配额
  quotaEl.textContent = '';
}

// ═══════════════════════════════════════════════════════════════
// 弹框工厂（私有）
// ═══════════════════════════════════════════════════════════════

let _popupZ = 1000;
const _popupStack = [];

function _animations() {
  if (document.getElementById('popup-anims')) return;
  const s = document.createElement('style'); s.id = 'popup-anims';
  s.textContent = '@keyframes fadeIn{from{opacity:0}to{opacity:1}}@keyframes slideUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}';
  document.head.appendChild(s);
}

/**
 * @param {string}  icon        Font Awesome 图标名（不含 fa- 前缀的不加）
 * @param {string}  iconBg      图标圆形背景 CSS
 * @param {string}  title       主文案
 * @param {string}  subtitle    副文案（可选）
 * @param {Array}   buttons     [{ text, style:'primary'|'danger'|'secondary', value, close:bool }]
 * @param {number}  autoCloseMs 自动关闭毫秒数，0=不自动关
 * @param {*}       dismissVal  点击遮罩关闭时的返回值
 */
function _createPopup({
  icon,
  iconBg,
  title,
  subtitle = '',
  buttons = [{ text: '确定', style: 'primary', value: null, close: true }],
  autoCloseMs = 0,
  dismissVal = null,
}) {
  _animations();
  const z = ++_popupZ;

  const overlay = document.createElement('div');
  overlay.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);display:flex;justify-content:center;align-items:center;z-index:${z};animation:fadeIn .3s ease;`;

  const modal = document.createElement('div');
  modal.style.cssText = 'background:#fff;border-radius:16px;padding:32px;text-align:center;max-width:380px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,.3);animation:slideUp .3s ease;';

  const btnBg = {
    primary: 'linear-gradient(135deg,#3B82F6,#2563EB)',
    danger: 'linear-gradient(135deg,#EF4444,#DC2626)',
    secondary: '#F3F4F6',
  };
  const btnColor = { primary: '#fff', danger: '#fff', secondary: '#374151' };

  const btnHtml = buttons.map((b, i) => {
    const bg = btnBg[b.style] || btnBg.primary;
    const color = btnColor[b.style] || '#fff';
    const border = b.style === 'secondary' ? 'border:1px solid #E5E7EB;' : 'border:none;';
    return `<button class="pu-btn-${i}" style="${border}background:${bg};color:${color};padding:12px 28px;border-radius:8px;font-size:15px;font-weight:500;cursor:pointer;">${b.text}</button>`;
  }).join('');

  const gap = subtitle ? '8px' : '24px';
  modal.innerHTML = `
    <div style="width:64px;height:64px;background:${iconBg};border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;">
      <i class="fas ${icon}" style="color:#fff;font-size:28px;"></i>
    </div>
    <h3 style="color:#111827;font-size:18px;font-weight:600;margin:0 0 ${gap} 0;line-height:1.5;">${title}</h3>
    ${subtitle ? `<p style="color:#6B7280;font-size:14px;margin:0 0 24px 0;line-height:1.5;">${subtitle}</p>` : ''}
    <div style="display:flex;gap:12px;justify-content:center;">${btnHtml}</div>
  `;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  let closed = false;
  let _resolve = null;

  const close = (result) => {
    if (closed) return;
    closed = true;
    overlay.remove();
    const idx = _popupStack.indexOf(entry);
    if (idx !== -1) _popupStack.splice(idx, 1);
    if (_resolve) _resolve(result);
  };

  const entry = { overlay, close };

  // 按钮事件
  buttons.forEach((b, i) => {
    const el = modal.querySelector(`.pu-btn-${i}`);
    if (el) el.addEventListener('click', () => { if (b.close !== false) close(b.value); });
  });

  // 遮罩点击
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(dismissVal); });

  // 自动关闭
  if (autoCloseMs > 0) setTimeout(() => close(), autoCloseMs);

  _popupStack.push(entry);

  // 暴露 resolve 供 showConfirm 的 Promise 用
  entry._setResolve = (fn) => { _resolve = fn; };

  return entry;
}

// ESC 关闭顶层弹框
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && _popupStack.length > 0) {
    _popupStack[_popupStack.length - 1].close();
  }
});

// ═══════════════════════════════════════════════════════════════
// 公开函数（签名不变）
// ═══════════════════════════════════════════════════════════════

function showError(msg) {
  _createPopup({
    icon: 'fa-exclamation-circle',
    iconBg: 'linear-gradient(135deg,#EF4444,#DC2626)',
    title: msg,
    buttons: [{ text: '确定', style: 'danger', value: null, close: true }],
  });
}

function showSuccess(message, subMessage = '') {
  _createPopup({
    icon: 'fa-check',
    iconBg: 'linear-gradient(135deg,#10B981,#059669)',
    title: message,
    subtitle: subMessage,
    buttons: [{ text: '确定', style: 'primary', value: null, close: true }],
    autoCloseMs: 3000,
  });
}

function showConfirm(message, confirmText = '确定', cancelText = '取消') {
  return new Promise((resolve) => {
    const entry = _createPopup({
      icon: 'fa-exclamation-triangle',
      iconBg: 'linear-gradient(135deg,#F59E0B,#D97706)',
      title: message,
      buttons: [
        { text: cancelText, style: 'secondary', value: false, close: true },
        { text: confirmText, style: 'primary', value: true, close: true },
      ],
      dismissVal: false,
    });
    entry._setResolve(resolve);
  });
}

// ═══════════════════════════════════════════════════════════════
// 其他组件
// ═══════════════════════════════════════════════════════════════

function getQueryParam(name) {
  return (new URLSearchParams(window.location.search)).get(name);
}

// 渲染页脚信息
function renderFooterInfo(pageType = 'default') {
  const footerInfo = document.createElement('div');
  footerInfo.className = 'footer-info';

  const map = {
    diagnose: '<div class="privacy-note"><i class="fas fa-lock"></i><span>隐私保护: 您的简历文件已处理完成并从服务器删除</span></div>',
    index:   '<div class="privacy-note"><i class="fas fa-lock"></i><span>安全提示：上传的文件仅用于AI分析，不会存储或用于其他目的,分析完成后立即删除</span></div>',
    optimization: '<div class="privacy-note"><i class="fas fa-lock"></i><span>隐私提示：您的简历内容仅用于本次优化分析，完成后会自动清除</span></div>',
    payment: '<p>我们重视您的隐私，所有支付信息均通过加密通道传输，确保安全</p><div class="privacy-note"><i class="fas fa-lock"></i><span>安全提示：支付过程中请勿泄露个人信息，如有疑问请联系客服</span></div>',
  };

  if (pageType === 'payok') return null;

  footerInfo.innerHTML = map[pageType] || map.index || '';
  return footerInfo;
}

export {
  renderFooterInfo,
  showError,
  showConfirm,
  showSuccess,
  getQueryParam,
  initUserState,
};
