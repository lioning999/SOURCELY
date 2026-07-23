/**
 * preview.html — 优化预览：AI 全文优化 + before/after 对比
 */
import { getToken } from '../api/core.js';
import { previewResume } from '../api/resume.js';

// ── DOM ─────────────────────────────────────────────────
const stateLoading  = document.getElementById('stateLoading');
const stateError    = document.getElementById('stateError');
const mainContent   = document.getElementById('mainContent');
const loadingMsg    = document.getElementById('loadingMsg');
const loadingTimer  = document.getElementById('loadingTimer');
const errorMsg      = document.getElementById('errorMsg');
const btnRetry      = document.getElementById('btnRetry');
const compareList   = document.getElementById('compareList');
const dimScan       = document.getElementById('dimensionScan');
const principlesLine = document.getElementById('principlesLine');
const btnPay        = document.getElementById('btnPay');
let diagnosisId = null;

// ── 显示切换 ────────────────────────────────────────────

function hideAll() {
  [stateLoading, stateError, mainContent].forEach(
    el => el.style.display = 'none');
}

function showOnly(el) { hideAll(); el.style.display = ''; }

// ── 参数 ────────────────────────────────────────────────

function getDiagnosisId() {
  return (new URLSearchParams(window.location.search)).get('diagnosis_id')
      || sessionStorage.getItem('lastDiagnosisId');
}

// ── 等待文案轮播 ──────────────────────────────────────────

const PREVIEW_PHRASES = [
  '正在逐段重写…',
  '正在匹配动词优化规则…',
  '正在生成 before/after 对比…',
  '正在检查数字锚点…',
  '正在调整句式结构…',
];

let phraseInterval = null;

function startPhrases() {
  let i = 0;
  loadingTimer.textContent = PREVIEW_PHRASES[0];
  phraseInterval = setInterval(() => {
    i = (i + 1) % PREVIEW_PHRASES.length;
    loadingTimer.textContent = PREVIEW_PHRASES[i];
  }, 3000);
}

function stopPhrases() {
  if (phraseInterval) { clearInterval(phraseInterval); phraseInterval = null; }
}

// ── 重试（409 冲突时）────────────────────────────────────

async function retryWithBackoff(fn, maxRetries, baseMs) {
  let delay = baseMs;
  for (let i = 0; i < maxRetries; i++) {
    await new Promise(r => setTimeout(r, delay));
    try {
      return await fn();
    } catch (e) {
      if (e.code === 409 && i < maxRetries - 1) { delay = Math.min(delay * 2, 8000); continue; }
      throw e;
    }
  }
}

// ── 渲染 ────────────────────────────────────────────────

function renderDimScan() {
  const dims = ['资质门槛', '经历身份', '行为动词', '成果量化', '自评一致', '技能画像'];
  dimScan.innerHTML = dims.map(name =>
    `<div class="dim-item"><span class="dim-icon">✅</span>${name}</div>`
  ).join('');
}

function render(data) {
  // 六维扫描
  renderDimScan();

  const pairs = data.preview || [];
  if (pairs.length === 0) {
    compareList.innerHTML = '<p style="text-align:center;color:var(--text-soft);padding:var(--sp-6);">暂无预览内容</p>';
  } else {
    compareList.innerHTML = pairs.map((p, i) => `
      <div style="margin-bottom:6px;font-size:var(--fs-rp);font-weight:650;color:var(--danger);padding-left:4px;">
        ${escHtml(p.issue_title || `优化项 ${i + 1}`)}
      </div>
      <div class="preview-compare">
        <div class="preview-col before">
          <div class="col-label">优化前</div>
          <p>${escHtml(p.before)}</p>
        </div>
        <div class="preview-col after">
          <div class="col-label">优化后</div>
          <p>${p.after ? escHtml(p.after) : '<span style="color:var(--text-fade);font-style:italic;">（已删除）</span>'}</p>
        </div>
      </div>
      ${p.reason ? `<div style="font-size:var(--fs-xs);color:var(--text-soft);margin-top:2px;padding-left:4px;">💡 ${escHtml(p.reason)}</div>` : ''}
    `).join('');
  }

  btnPay.href = data.is_paid
    ? `result.html?diagnosis_id=${encodeURIComponent(data.diagnosis_id || diagnosisId)}`
    : `payment.html?diagnosis_id=${encodeURIComponent(data.diagnosis_id || diagnosisId)}`;
  btnPay.textContent = data.is_paid ? '查看完整结果 →' : '打赏 ¥1 解锁完整结果 →';

  // 优化原则提示
  principlesLine.textContent = '改写原则：保留真实经历 · 调整表达 · 补充数据支撑';
  principlesLine.style.display = '';

  showOnly(mainContent);
}

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── 主流程 ──────────────────────────────────────────────

async function loadPreview() {
  // 登录门禁（先检查，避免 loading 闪现）
  if (!getToken()) { window.location.href = 'index.html'; return; }

  // 检查参数
  diagnosisId = getDiagnosisId();
  if (!diagnosisId) {
    showOnly(stateError);
    errorMsg.textContent = '缺少诊断ID，请先诊断简历';
    return;
  }

  showOnly(stateLoading);
  loadingMsg.textContent = 'AI 正在逐段重写你的简历…';
  loadingTimer.textContent = '';
  startPhrases();

  let result;
  try {
    result = await retryWithBackoff(
      () => previewResume(diagnosisId), 4, 1000);
  } catch (e) {
    stopPhrases();
    showOnly(stateError);
    errorMsg.textContent = e.message || '优化失败，请重试';
    return;
  }
  stopPhrases();

  render(result);
}

btnRetry.addEventListener('click', () => {
  btnRetry.disabled = true;
  btnRetry.textContent = '加载中…';
  loadPreview().finally(() => {
    btnRetry.disabled = false;
    btnRetry.textContent = '重新尝试';
  });
});

// ── 启动 ────────────────────────────────────────────────

loadPreview();
