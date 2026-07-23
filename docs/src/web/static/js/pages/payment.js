/**
 * payment.html — 支付页：确认 → 创建订单 → 扫码 → 轮询 → 跳转结果
 */
import { getToken } from '../api/core.js';
import { createOrder, queryOrder } from '../api/payment.js';

// ── DOM ─────────────────────────────────────────────────
const stateLogin    = document.getElementById('stateLogin');
const stateLoading  = document.getElementById('stateLoading');
const stateError    = document.getElementById('stateError');
const stateConfirm  = document.getElementById('stateConfirm');
const stateQr       = document.getElementById('stateQr');
const errorMsg      = document.getElementById('errorMsg');
const btnRetry      = document.getElementById('btnRetry');
const btnConfirm    = document.getElementById('btnConfirm');
const btnManual     = document.getElementById('btnManualCheck');
const btnReOrder    = document.getElementById('btnReOrder');
const qrImage       = document.getElementById('qrImage');
const qrAmount      = document.getElementById('qrAmount');


const payStatus     = document.getElementById('payStatus');
const payTimer      = document.getElementById('payTimer');
const payActions    = document.getElementById('payActions');
const payManual     = document.getElementById('payManual');
const POLL_INTERVAL = 3000;
const PAY_TIMEOUT   = 300000; // 5 分钟
let pollHandle = null;
let diagnosisId = null;
let outTradeNo = null;
let pollStartTime = null;

// ── 显示切换 ────────────────────────────────────────────

function showOnly(el) {
  [stateLogin, stateLoading, stateError, stateConfirm, stateQr].forEach(
    e => e.style.display = 'none');
  el.style.display = '';
}

// ── 参数 ────────────────────────────────────────────────

function getDiagnosisId() {
  return (new URLSearchParams(window.location.search)).get('diagnosis_id')
      || sessionStorage.getItem('lastDiagnosisId');
}

// ── 步骤一：确认 → 创建订单 → 展示二维码 ──────────────────

async function onConfirm() {
  btnConfirm.disabled = true;
  btnConfirm.textContent = '创建订单中…';
  showOnly(stateLoading);

  let order;
  try {
    order = await createOrder(1, diagnosisId);
  } catch (e) {
    showOnly(stateError);
    errorMsg.textContent = e.message || '创建订单失败';
    btnConfirm.disabled = false;
    btnConfirm.textContent = '确认打赏 ¥1 →';
    return;
  }

  outTradeNo = order.out_trade_no;
  window.__outTradeNo = outTradeNo;

  // 渲染二维码
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(order.qr_code_url)}`;
  qrImage.src = qrUrl;
  const amount = (order.amount / 100).toFixed(2);
  qrAmount.textContent = `¥${amount}`;

  showOnly(stateQr);
  startPolling();
}

btnConfirm.addEventListener('click', onConfirm);

// ── 步骤二：轮询支付状态 ──────────────────────────────────

function startPolling() {
  pollStartTime = Date.now();
  payTimer.textContent = '订单 5 分钟内有效';
  payStatus.innerHTML = '<span class="spinner" style="width:16px;height:16px;"></span> 等待支付…';
  payActions.style.display = 'none';
  payManual.style.display = '';

  pollHandle = setInterval(async () => {
    const elapsed = Date.now() - pollStartTime;
    const remainMin = Math.max(1, Math.ceil((PAY_TIMEOUT - elapsed) / 60000));

    if (elapsed >= PAY_TIMEOUT) {
      stopPolling();
      payStatus.innerHTML = '⏰ 支付超时';
      payTimer.textContent = '请重新下单';
      payManual.style.display = 'none';
      payActions.style.display = 'block';
      return;
    }

    payTimer.textContent = `剩余约 ${remainMin} 分钟`;

    try {
      const result = await queryOrder(outTradeNo);
      if (result.status === 'paid') {
        stopPolling();
        payStatus.innerHTML = '✅ 支付成功，正在跳转…';
        payTimer.textContent = '';
        payManual.style.display = 'none';
        setTimeout(() => {
          window.location.href = `result.html?diagnosis_id=${encodeURIComponent(diagnosisId)}`;
        }, 600);
      }
    } catch (e) {
      console.warn('Order poll error:', e.message);
    }
  }, POLL_INTERVAL);
}

function stopPolling() {
  if (pollHandle) { clearInterval(pollHandle); pollHandle = null; }
}

// ── 手动查询 ────────────────────────────────────────────

btnManual.addEventListener('click', async () => {
  btnManual.disabled = true;
  btnManual.textContent = '查询中…';
  try {
    const result = await queryOrder(outTradeNo);
    if (result.status === 'paid') {
      stopPolling();
      payStatus.innerHTML = '✅ 支付成功，正在跳转…';
      payTimer.textContent = '';
      payManual.style.display = 'none';
      setTimeout(() => {
        window.location.href = `result.html?diagnosis_id=${encodeURIComponent(diagnosisId)}`;
      }, 600);
    } else {
      Toast.success('暂未收到支付通知，请确认是否已完成支付');
    }
  } catch (e) {
    Toast.error('查询失败，请重试');
  }
  btnManual.disabled = false;
  btnManual.textContent = '我已支付，查看结果';
});

// ── 重新下单 ────────────────────────────────────────────

btnReOrder.addEventListener('click', () => {
  stopPolling();
  btnConfirm.disabled = false;
  btnConfirm.textContent = '确认打赏 ¥1 →';
  showOnly(stateConfirm);
});

// ── 重试（错误态） ────────────────────────────────────────

btnRetry.addEventListener('click', () => {
  btnRetry.disabled = true;
  btnRetry.textContent = '创建中…';
  onConfirm().finally(() => {
    btnRetry.disabled = false;
    btnRetry.textContent = '重新创建订单';
  });
});

// ── 启动 ────────────────────────────────────────────────

function init() {
  if (!getToken()) { window.location.href = 'index.html'; return; }

  diagnosisId = getDiagnosisId();
  if (!diagnosisId) {
    showOnly(stateError);
    errorMsg.textContent = '缺少诊断ID，请先诊断简历';
    return;
  }

  // 先展示确认页，不创建订单
  showOnly(stateConfirm);
}

init();
