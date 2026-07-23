/**
 * diagnosis.html — 诊断报告：动态渲染 AI 诊断结果
 */
import { getToken } from '../api/core.js';
import { getDiagnosis } from '../api/resume.js';

// ── DOM 引用 ────────────────────────────────────────────
const stateLoading   = document.getElementById('stateLoading');
const stateError     = document.getElementById('stateError');
const stateEmpty     = document.getElementById('stateEmpty');
const mainContent    = document.getElementById('mainContent');
const errorMsg       = document.getElementById('errorMsg');
const overallEl      = document.getElementById('overallImpression');
const dimScanEl      = document.getElementById('dimensionScan');
const fatalTitle     = document.getElementById('fatalTitle');
const fatalList      = document.getElementById('fatalList');
const fatalCard      = document.getElementById('fatalCard');
const targetCard     = document.getElementById('targetCard');
const targetTitle    = document.getElementById('targetTitle');
const targetList     = document.getElementById('targetList');
const btnPreview     = document.getElementById('btnPreview');
const btnHint        = document.getElementById('btnHint');
let diagnosisId = null;

// ── 数据加载 ────────────────────────────────────────────

function getDiagnosisId() {
  const p = new URLSearchParams(window.location.search);
  return p.get('diagnosis_id') || sessionStorage.getItem('lastDiagnosisId');
}

function loadCachedResult() {
  try {
    const raw = sessionStorage.getItem('lastDiagnosisResult');
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

// ── 渲染 ────────────────────────────────────────────────

function show(el) { el.style.display = ''; }
function hide(el) { el.style.display = 'none'; }
function showOnly(el) {
  [stateLoading, stateError, stateEmpty, mainContent].forEach(hide);
  show(el);
}

function render(data) {
  if (!data) { showOnly(stateEmpty); return; }

  diagnosisId = data.diagnosis_id;

  // 重复诊断提示
  if (data.is_rediagnosis) {
    const hint = document.getElementById('rediagnosisHint');
    if (hint) hint.style.display = '';
  }

  // 整体印象 — 按句号拆行，首行加粗
  const raw = data.overall_impression || '';
  const sentences = raw.split(/[。！]/).filter(s => s.trim());
  if (sentences.length > 1) {
    overallEl.innerHTML = `<div class="impression-verdict">${escHtml(sentences[0].trim())}</div>
      <div class="impression-detail">${escHtml(sentences.slice(1).join('。').trim())}</div>`;
  } else {
    overallEl.innerHTML = `<div class="impression-verdict">${escHtml(raw)}</div>`;
  }

  // 六维扫描 — emoji + 文字标签
  const scan = data.dimension_scan;
  const dimLabels = { '✅': '通过', '❌': '未过', '⚠️': '预警' };
  if (scan) {
    if (dimScanEl) {
      dimScanEl.innerHTML = Object.entries(scan).map(([name, status]) => {
        const icon = status === '✅' ? '✅' : status === '❌' ? '❌' : '⚠️';
        const label = dimLabels[icon] || '';
        return `<div class="dim-item"><span class="dim-icon">${icon}</span>${name}<span class="dim-label"> ${label}</span></div>`;
      }).join('');
    }
  }

  // 致命问题
  const fatals = data.fatal_issues || [];
  if (fatals.length === 0) {
    hide(fatalCard);
  } else {
    show(fatalCard);
    fatalTitle.textContent = `致命问题 ${fatals.length} 个`;
    fatalList.innerHTML = fatals.map((f, i) => {
      const sevColors = { high: 'var(--danger)', medium: '#E8856C', low: '#F59E0B' };
      const borderColor = sevColors[f.severity] || sevColors.medium;
      const sevLabel = { high: '严重', medium: '中等', low: '轻微' }[f.severity] || '';
      // 修复难度：含数字/量化/动词关键词 → 可立即修复
      const text = (f.title + f.description).toLowerCase();
      const easy = /数字|量化|动词|锚点|负责|参与|成果|数据/.test(text);
      const fixCls = easy ? 'fix-easy' : 'fix-deep';
      const fixLabel = easy ? '可立即修复' : '需深度改写';
      return `<div class="fatal-item" style="border-left-color:${borderColor}">
        <div class="fatal-label">致命问题 ${i + 1}<span style="color:${borderColor};margin-left:8px;">${sevLabel}</span><span class="fix-tag ${fixCls}">${fixLabel}</span></div>
        <div class="fatal-title">${escHtml(f.title)}</div>
        <div class="fatal-desc">${escHtml(f.description).replace(/\n/g, '<br>')}</div>
      </div>`;
    }).join('');
  }

  // 追问靶子
  const targets = data.interview_targets || [];
  if (targets.length === 0) {
    hide(targetCard);
  } else {
    show(targetCard);
    targetTitle.textContent = `面试追问靶子 ${targets.length} 个`;
    targetList.innerHTML = targets.map(t =>
      `<div class="list-item"><span class="bullet red"></span>${escHtml(t.target || t.question || t.title)}</div>`
    ).join('');
  }

  // 按钮：预览免费，直接跳转
  btnPreview.href = `preview.html?diagnosis_id=${encodeURIComponent(diagnosisId)}`;
  btnPreview.textContent = '进入优化预览 →';
  btnHint.textContent = '免费预览 Top 2 优化对比，打赏 ¥1 解锁完整结果';

  showOnly(mainContent);
}

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── 启动 ────────────────────────────────────────────────

async function init() {
  // 未登录 → 跳首页
  if (!getToken()) {
    window.location.href = 'index.html';
    return;
  }

  diagnosisId = getDiagnosisId();
  if (!diagnosisId) {
    showOnly(stateEmpty);
    return;
  }

  // ① 优先 sessionStorage（刚完成诊断的即时数据）
  const cached = loadCachedResult();
  if (cached) {
    render(cached);
    return;
  }

  // ② 从后端加载（首页记录跳转、刷新恢复等场景）
  try {
    const data = await getDiagnosis(diagnosisId);
    if (data) {
      // 缓存到 sessionStorage，下次直接读
      sessionStorage.setItem('lastDiagnosisResult', JSON.stringify(data));
      render(data);
      return;
    }
  } catch (e) {
    console.warn('加载诊断数据失败:', e.message);
  }

  showOnly(stateError);
  errorMsg.textContent = '诊断数据加载失败';
}

init();
