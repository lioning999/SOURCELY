/**
 * result.html — 优化结果：全文简历 + before/after 对比
 */
import { getToken } from '../api/core.js';
import { getOptimizeResult } from '../api/resume.js';

// ── DOM ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const stateLoading = $('stateLoading'), stateLogin = $('stateLogin');
const stateError = $('stateError'), stateEmpty = $('stateEmpty');
const statePay = $('statePay'), mainContent = $('mainContent');
const errorMsg = $('errorMsg'), btnRetry = $('btnRetry');
const btnBuyR = $('btnBuyFromResult');
const optimizedText = $('optimizedText'), compareBody = $('compareBody');
const compareCard = $('compareCard'), compareTitle = $('compareTitle');
const headerResume = $('headerResume'), bodyResume = $('bodyResume');
const headerCompare = $('headerCompare'), bodyCompare = $('bodyCompare');
const chevronCompare = $('chevronCompare');
const resultSummary = $('resultSummary');
const resultPrinciples = $('resultPrinciples');
const btnToQA = $('btnToQA');

let diagnosisId = null;

// ── 显示切换 ────────────────────────────────────────────

const ALL_STATES = [stateLoading, stateLogin, stateError, stateEmpty, statePay, mainContent];
function showOnly(el) { ALL_STATES.forEach(e => e.style.display = 'none'); el.style.display = ''; }

// ── 参数 ────────────────────────────────────────────────

function getDiagnosisId() {
  return (new URLSearchParams(window.location.search)).get('diagnosis_id')
      || sessionStorage.getItem('lastDiagnosisId');
}

// ── 格式化优化后简历 ──────────────────────────────────────

function formatOptimizedText(text) {
  if (!text) return '';
  // 先转义，再转换 markdown 语法
  let html = escHtml(text);
  // ## 标题 → <h3>
  html = html.replace(/^## (.+)$/gm, '<h3 class="opt-heading">$1</h3>');
  // ### 子标题 → <h4>
  html = html.replace(/^### (.+)$/gm, '<h4 class="opt-subheading">$1</h4>');
  // **加粗**
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // 连续换行 → 段落分隔
  html = html.replace(/\n\n+/g, '</p><p>');
  // 单换行 → <br>
  html = html.replace(/\n/g, '<br>');
  return '<p>' + html + '</p>';
}

// ── HTML 转义 ──────────────────────────────────────────

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── 折叠面板 ────────────────────────────────────────────

function setupToggle(header, body, chevron) {
  header.addEventListener('click', () => {
    const isOpen = body.classList.toggle('open');
    header.classList.toggle('open');
    if (chevron) chevron.textContent = isOpen ? '▾' : '▸';
  });
}

// ── 进度条 ──────────────────────────────────────────────

function render(data) {
  // 修复摘要
  const summary = data.diagnose_summary;
  if (summary && summary.overall_impression) {
    const firstLine = summary.overall_impression.split(/[。！]/)[0];
    resultSummary.innerHTML = `<div class="impression-verdict">已修复 ${summary.fatal_count || 0} 个致命问题</div>
      <div class="impression-detail">${escHtml(firstLine.trim())}</div>`;
  } else {
    resultSummary.style.display = 'none';
  }

  // 优化后简历 — 格式化为可读 HTML
  optimizedText.innerHTML = formatOptimizedText(data.optimized_text || '');

  // before/after 对比 — 使用 issue_title
  const pairs = data.before_after_pairs || [];
  if (pairs.length === 0) {
    compareCard.style.display = 'none';
  } else {
    compareTitle.textContent = `改了什么（${pairs.length} 处对比）`;
    compareBody.innerHTML = pairs.map((p, i) => `
      <div style="margin-bottom:4px;font-size:var(--fs-xs);font-weight:650;color:var(--danger);padding-left:4px;">
        ${escHtml(p.issue_title || `对比 ${i + 1}`)}
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

    // 优化原则
    resultPrinciples.textContent = '改写原则：保留真实经历 · 调整表达 · 补充数据支撑';
    resultPrinciples.style.display = '';
  }

  // 追问预判入口 — 跳转 interview-qa.html
  btnToQA.href = `interview-qa.html?diagnosis_id=${encodeURIComponent(diagnosisId)}`;

  showOnly(mainContent);
}

// ── 主流程 ──────────────────────────────────────────────

async function loadResult() {
  // 登录门禁先检查
  if (!getToken()) { window.location.href = 'index.html'; return; }

  diagnosisId = getDiagnosisId();
  if (!diagnosisId) { showOnly(stateEmpty); return; }

  showOnly(stateLoading);

  let result;
  try {
    result = await getOptimizeResult(diagnosisId);
  } catch (e) {
    if (e.code === 402) {
      btnBuyR.href = `payment.html?diagnosis_id=${encodeURIComponent(diagnosisId)}`;
      showOnly(statePay);
    } else {
      showOnly(stateError);
      errorMsg.textContent = e.message || '加载优化结果失败';
    }
    return;
  }

  render(result);
}

btnRetry.addEventListener('click', () => {
  btnRetry.disabled = true;
  btnRetry.textContent = '加载中…';
  loadResult().finally(() => {
    btnRetry.disabled = false;
    btnRetry.textContent = '重新加载';
  });
});

// ── 启动 ────────────────────────────────────────────────

setupToggle(headerResume, bodyResume);
setupToggle(headerCompare, bodyCompare, chevronCompare);
loadResult();
