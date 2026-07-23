/**
 * interview-hub.js — 模拟面试：AI 面试题 + 模拟作答 + 面试工具箱
 *
 * 入口路径：interview-qa → 下一步（带 diagnosis_id）
 * 登录 + 有 diagnosis_id → 调 AI；否则展示空状态引导
 */
import { callApi, getToken } from '../api/core.js';

// ── sessionStorage keys ─────────────────────────────────
const KEYS = {
  FEEDBACK_PREFIX: 'feedback_',
};

// ── DOM ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const stateLogin   = $('stateLogin');
const stateEmpty   = $('stateEmpty');
const stateLoading = $('stateLoading');
const stateError   = $('stateError');
const mainContent  = $('mainContent');
const errorMsg     = $('errorMsg');
const btnRetry     = $('btnRetry');
const questionList = $('questionList');
const feedbackBar  = $('feedbackBar');
const fbGood       = $('fbGood');
const fbBad        = $('fbBad');
const feedbackThanks = $('feedbackThanks');

// ── 状态检测 ────────────────────────────────────────────
const token = getToken();

// ── 显示切换 ────────────────────────────────────────────
const ALL_STATES = [stateLogin, stateEmpty, stateLoading, stateError, mainContent];
function showOnly(el) { ALL_STATES.forEach(e => e.style.display = 'none'); el.style.display = ''; }

// ── 渲染面试题 ──────────────────────────────────────────
function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderQuestions(questions) {
  questionList.innerHTML = questions.map((item, i) => `
    <div class="question-card">
      <div class="question-top">
        <span class="question-num">${String(i + 1).padStart(2, '0')}</span>
        <span class="question-text">${esc(item.q)}</span>
        <span class="difficulty-tag ${item.difficultyClass || 'base'}">${esc(item.difficulty || '基础')}</span>
      </div>
      <div class="question-meta">
        <div class="meta-item"><span class="mi-icon">👁</span><span>面试官意图：${esc(item.intent)}</span></div>
        <div class="meta-item"><span class="mi-icon">💡</span><span>${esc(item.hint)}</span></div>
      </div>
      <div class="mock-section">
        <span class="mock-trigger" onclick="window._toggleMock(this, ${i})">✏ 模拟作答</span>
        <div class="mock-area" id="mockArea${i}">
          <textarea placeholder="在这里写出你的回答…" id="mockInput${i}"></textarea>
          <button class="mock-submit" onclick="window._submitMock(${i})">✨ 提交并对比参考话术</button>
          <div class="mock-result" id="mockResult${i}">
            <div class="compare-grid">
              <div class="compare-col user"><h4>📝 你的回答</h4><p id="userAnswer${i}"></p></div>
              <div class="compare-col ref"><h4>⭐ 参考话术</h4><p>${esc(item.reference)}</p></div>
            </div>
            <div class="self-check">
              <strong>✅ 自我检查清单：</strong>
              <li>你是否提到了具体的经历和数据？</li>
              <li>你的回答是否有清晰的结构（情境→任务→行动→结果）？</li>
              <li>你的回答是否控制在1-2分钟内？</li>
              <li>你是否表达了明确的求职动机或职业思考？</li>
            </div>
          </div>
        </div>
      </div>
    </div>
  `).join('');
}

// ── 模拟作答交互 ────────────────────────────────────────
function toggleMock(triggerEl, index) {
  const area = document.getElementById('mockArea' + index);
  if (area.classList.contains('active')) {
    area.classList.remove('active');
    triggerEl.textContent = '✏ 模拟作答';
  } else {
    area.classList.add('active');
    triggerEl.textContent = '✕ 收起';
    setTimeout(() => { const inp = document.getElementById('mockInput' + index); if (inp) inp.focus(); }, 100);
  }
}

function submitMock(index) {
  const input = document.getElementById('mockInput' + index);
  const answer = input.value.trim();
  if (!answer) {
    input.style.borderColor = 'var(--danger)';
    input.placeholder = '请先输入你的回答再提交！';
    input.focus();
    setTimeout(() => { input.style.borderColor = ''; }, 1500);
    return;
  }
  document.getElementById('userAnswer' + index).textContent = answer;
  const result = document.getElementById('mockResult' + index);
  result.classList.add('active');
  result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── 反馈 ────────────────────────────────────────────────
async function doFeedback(rating) {
  try {
    await callApi('/resume/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'interview', rating }),
    });
  } catch (_) { /* 非关键路径 */ }
  document.getElementById('feedbackActions').style.display = 'none';
  feedbackThanks.style.display = 'block';
  sessionStorage.setItem(KEYS.FEEDBACK_PREFIX + 'interview', '1');
}

// ── 工具箱 accordion ────────────────────────────────────
function initToolbox() {
  document.querySelectorAll('.tb-trigger').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.parentElement;
      const isOpen = item.classList.contains('open');
      // 关掉所有
      document.querySelectorAll('.tb-item.open').forEach(el => el.classList.remove('open'));
      // 如果之前没开 → 打开
      if (!isOpen) item.classList.add('open');
    });
  });
}

// ── API ─────────────────────────────────────────────────

function getDiagnosisId() {
  return (new URLSearchParams(window.location.search)).get('diagnosis_id')
      || sessionStorage.getItem('lastDiagnosisId');
}

/**
 * 获取 AI 个性化模拟面试题（5 道）。
 * 幂等：已有结果时直接返回缓存，秒开。
 */
async function fetchInterviewQuestions(diagnosisId) {
  if (!diagnosisId) throw new Error('diagnosisId 不能为空');

  const result = await callApi('/resume/interview-questions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ diagnosis_id: diagnosisId }),
  });

  return result.data;
}

/** 将 API 返回格式映射为 renderQuestions 使用的字段名 */
function mapToRender(questions) {
  const DIFF_MAP = { '必问': 'must', '高频': 'high', '基础': 'base' };
  return questions.map(q => ({
    q: q.question || '',
    intent: q.intent || '',
    difficulty: q.difficulty || '基础',
    difficultyClass: DIFF_MAP[q.difficulty] || 'base',
    hint: q.hint || '',
    reference: q.reference || '',
  }));
}

// ── 主流程 ──────────────────────────────────────────────
async function load() {
  if (!token) { window.location.href = 'index.html'; return; }

  const diagnosisId = getDiagnosisId();
  if (!diagnosisId) { showOnly(stateEmpty); return; }

  showOnly(stateLoading);
  try {
    const data = await fetchInterviewQuestions(diagnosisId);
    const questions = data.questions || [];
    if (questions.length === 0) {
      showOnly(stateEmpty);
      return;
    }
    renderQuestions(mapToRender(questions));
    initToolbox();
    showOnly(mainContent);
    if (!sessionStorage.getItem(KEYS.FEEDBACK_PREFIX + 'interview')) {
      feedbackBar.style.display = '';
    }
  } catch (e) {
    console.warn('[模拟面试] load 失败:', e.message);
    if (e.code === 402) {
      // 未付费：展示付费引导
      errorMsg.innerHTML = '请先完成优化。'
        + '<br><small style=\"color:var(--text-fade);\">打赏 ¥1 解锁 AI 优化 + 追问预判 + 模拟面试</small>';
      btnRetry.textContent = '打赏 ¥1 →';
      btnRetry.onclick = () => {
        window.location.href = `payment.html?diagnosis_id=${encodeURIComponent(diagnosisId)}`;
      };
    } else {
      errorMsg.textContent = e.message || '加载面试题失败，请重试';
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
  load().finally(() => {
    btnRetry.disabled = false;
    btnRetry.textContent = '重新生成';
  });
});

// ── 反馈按钮 ────────────────────────────────────────────
fbGood.addEventListener('click', () => { fbGood.classList.add('active'); doFeedback(1); });
fbBad.addEventListener('click', () => { fbBad.classList.add('active'); doFeedback(-1); });

// ── 暴露到 window（HTML onclick 调用）───────────────────
window._toggleMock = toggleMock;
window._submitMock = submitMock;

// ── 启动 ────────────────────────────────────────────────
load();
