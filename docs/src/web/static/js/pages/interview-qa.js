/**
 * interview-qa.html — 追问预判：AI 简历弱点追问靶子 + 答题思路
 */
import { callApi, getToken } from '../api/core.js';

// ── DOM ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const stateLogin   = $('stateLogin');
const stateLoading = $('stateLoading');
const stateError   = $('stateError');
const stateEmpty   = $('stateEmpty');
const mainContent  = $('mainContent');
const errorMsg     = $('errorMsg');
const btnRetry     = $('btnRetry');
const qaSummary    = $('qaSummary');
const qaList       = $('qaList');
const btnNext      = $('btnNext');

let diagnosisId = null;

// ── 显示切换 ────────────────────────────────────────────

const ALL_STATES = [stateLogin, stateLoading, stateError, stateEmpty, mainContent];
function showOnly(el) { ALL_STATES.forEach(e => e.style.display = 'none'); el.style.display = ''; }

// ── 参数 ────────────────────────────────────────────────

function getDiagnosisId() {
  return (new URLSearchParams(window.location.search)).get('diagnosis_id')
      || sessionStorage.getItem('lastDiagnosisId');
}

// ── API ─────────────────────────────────────────────────

/**
 * AI 生成面试追问预判 + resolved 标注，入库后返回。
 * 幂等：已有追问结果时直接返回缓存，秒开。
 */
async function getInterviewQA(diagnosisId) {
  if (!diagnosisId) throw new Error('diagnosisId 不能为空');

  const result = await callApi('/resume/interview-qa', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ diagnosis_id: diagnosisId }),
  });

  return result.data;
}

// ── 渲染 ────────────────────────────────────────────────

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function render(data) {
  const targets = data.targets || [];
  const summary = data.summary || {};

  // 摘要条
  if (summary.total) {
    qaSummary.textContent = `共 ${summary.total} 问 · ✅ ${summary.resolved || 0} 已化解 · ⚠️ ${summary.active || 0} 待准备`;
    qaSummary.style.display = '';
  } else {
    qaSummary.style.display = 'none';
  }

  if (targets.length === 0) {
    qaList.innerHTML = '<p style="text-align:center;color:var(--text-fade);padding:var(--sp-4);">暂无追问靶子</p>';
    showOnly(mainContent);
    return;
  }

  // 排序：待准备（active）在上，已化解（resolved）在下
  const sorted = [...targets].sort((a, b) => {
    if (a.status === 'active' && b.status !== 'active') return -1;
    if (a.status !== 'active' && b.status === 'active') return 1;
    return 0;
  });

  qaList.innerHTML = sorted.map((t, i) => {
    const isResolved = t.status === 'resolved';
    const borderColor = isResolved ? 'var(--success)' : '#E8856C';
    const statusBadge = isResolved ? '✅ 已化解' : '⚠️ 待准备';
    const layer = t.layer || 1;
    const layerLabel = t.layer_label || '';

    return `
      <div class="qa-card" style="border-left:3px solid ${borderColor};">
        <div class="qa-card-header">
          <div class="qa-card-header-left">
            <span class="qa-card-num">追问 ${i + 1}</span>
            ${layerLabel ? `<span class="qa-card-layer l${layer}">${escHtml(layerLabel)}</span>` : ''}
          </div>
          <span class="qa-card-status" style="color:${borderColor};">${statusBadge}</span>
        </div>
        <div class="qa-card-question">${escHtml(t.question || '')}</div>
        ${t.intent ? `<div class="qa-card-intent">🎯 面试官意图：${escHtml(t.intent)}</div>` : ''}
        <div class="qa-card-answer">
          <div class="qa-card-label">答题思路</div>
          <p>${escHtml(t.answer || '').replace(/\n/g, '<br>')}</p>
        </div>
        ${isResolved && t.resolved_by ? `
          <div class="qa-card-resolved">
            📌 优化后简历已覆盖：${escHtml(t.resolved_by)}
          </div>` : ''}
      </div>
    `;
  }).join('');

  // 下一步按钮（带 diagnosis_id，确保 interview-hub 能识别真实用户）
  btnNext.href = `interview-hub.html?diagnosis_id=${encodeURIComponent(diagnosisId)}`;

  showOnly(mainContent);
}

// ── 主流程 ──────────────────────────────────────────────

async function loadQA() {
  if (!getToken()) { window.location.href = 'index.html'; return; }

  diagnosisId = getDiagnosisId();
  if (!diagnosisId) { showOnly(stateEmpty); return; }

  showOnly(stateLoading);

  try {
    const data = await getInterviewQA(diagnosisId);
    render(data);
  } catch (e) {
    console.warn('[追问预判] loadQA 失败:', e.message);
    if (e.code === 402) {
      // 未付费：展示付费引导
      errorMsg.innerHTML = '请先完成优化。'
        + '<br><small style=\"color:var(--text-fade);\">打赏 ¥1 解锁 AI 优化 + 追问预判 + 模拟面试</small>';
      btnRetry.textContent = '打赏 ¥1 →';
      btnRetry.style.display = '';
      btnRetry.onclick = () => {
        window.location.href = `payment.html?diagnosis_id=${encodeURIComponent(diagnosisId)}`;
      };
    } else {
      errorMsg.textContent = e.message || '加载追问预判失败，请重试';
      btnRetry.textContent = '重新生成';
      btnRetry.onclick = null;
    }
    showOnly(stateError);
  }
}

// ── 重试 ────────────────────────────────────────────────

btnRetry.addEventListener('click', () => {
  btnRetry.disabled = true;
  btnRetry.textContent = '加载中…';
  loadQA().finally(() => {
    btnRetry.disabled = false;
    btnRetry.textContent = '重新加载';
  });
});

// ── 启动 ────────────────────────────────────────────────

loadQA();
