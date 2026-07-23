/**
 * index.html — 首页：上传简历 → AI 诊断 → 跳转诊断报告
 */
import { getToken, callApi } from '../api/core.js';
import { uploadResume, diagnoseResume } from '../api/resume.js';
import { showConfirm } from '../components.js';

// ── DOM 引用 ────────────────────────────────────────────
const uploadZone    = document.getElementById('uploadZone');
const fileInput     = document.getElementById('fileInput');
const btnSubmit     = document.getElementById('btnSubmit');
const upIcon        = document.getElementById('upIcon');
const upTitle       = document.getElementById('upTitle');
const upHint        = document.getElementById('upHint');
const uploadAnim    = document.getElementById('uploadAnim');
const animMsg       = document.getElementById('animMsg');
const animTimer     = document.getElementById('animTimer');
const historySection  = document.getElementById('historySection');
const historyLink    = document.getElementById('historyLink');
const hcDate         = document.getElementById('hcDate');
const hcSummary      = document.getElementById('hcSummary');

let selectedFile = null;
let busy = false;
let phraseInterval = null;

const DIAG_PHRASES = [
  '正在扫描动词使用…',
  '正在评估成果量化…',
  '正在检查自评一致性…',
  '正在识别经历身份…',
  '正在分析技能画像…',
  '正在核验资质门槛…',
];

// ── 登录态 ──────────────────────────────────────────────

initHistory();

function initHistory() {
  if (!getToken()) return;
  fetchLatest();
}

async function fetchLatest() {
  try {
    const result = await callApi('/resume/latest', { method: 'GET' });
    const d = result.data;
    if (!d) return;

    const date = new Date(d.created_at);
    const fatalText = d.fatal_count
      ? `致命问题 ${d.fatal_count} 个`
      : '已完成诊断';
    hcDate.textContent = `${date.getMonth() + 1}月${date.getDate()}日 诊断 · ${fatalText}`;

    const parts = [];
    if (d.steps.optimize) parts.push('已优化');
    if (d.steps.interview_qa) parts.push('追问已生成');
    if (d.steps.interview_questions) parts.push('模拟面试已完成');

    if (parts.length > 0) {
      hcSummary.textContent = parts.join(' · ');
    } else {
      // 只完成了诊断，显示整体印象摘要
      hcSummary.textContent = '待优化';
    }

    historyLink.href = `diagnosis.html?diagnosis_id=${encodeURIComponent(d.diagnosis_id)}`;
    historySection.style.display = '';
  } catch (e) {
    console.warn('fetchLatest 失败:', e.message);
  }
}

// ── 文件选择 ────────────────────────────────────────────

uploadZone.addEventListener('click', () => {
  if (!busy) fileInput.click();
});

fileInput.addEventListener('change', () => {
  const f = fileInput.files[0];
  if (f) handleFile(f);
});

uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) handleFile(f);
});

function handleFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (['pdf', 'docx', 'txt', 'doc'].indexOf(ext) === -1) {
    Toast.error('仅支持 PDF、Word、TXT 格式');
    return;
  }
  selectedFile = file;
  renderSelected(file);
}

function renderSelected(file) {
  uploadZone.classList.add('selected');
  upIcon.textContent = '✅';
  upTitle.textContent = file.name;
  upTitle.style.color = 'var(--success)';
  upHint.textContent = `${(file.size / 1024).toFixed(0)} KB · ${file.name.split('.').pop().toUpperCase()}`;
  btnSubmit.disabled = false;
}

// ── 提交：上传 + 诊断 ───────────────────────────────────

btnSubmit.addEventListener('click', () => {
  if (!selectedFile || busy) return;
  startFlow();
});

function startPhrases() {
  let i = 0;
  animTimer.textContent = DIAG_PHRASES[0];
  phraseInterval = setInterval(() => {
    i = (i + 1) % DIAG_PHRASES.length;
    animTimer.textContent = DIAG_PHRASES[i];
  }, 2500);
}

function stopPhrases() {
  if (phraseInterval) { clearInterval(phraseInterval); phraseInterval = null; }
}

async function startFlow() {
  if (!getToken()) {
    window.location.href = '/auth/wechat-login';
    return;
  }
  busy = true;
  uploadZone.style.display = 'none';
  btnSubmit.style.display = 'none';
  uploadAnim.style.display = 'block';

  // ① 上传
  animMsg.textContent = '正在读取简历…';
  animTimer.textContent = '';

  let uploadResult;
  try {
    uploadResult = await uploadResume(selectedFile);
  } catch (e) {
    showRecover(`上传失败：${e.message}`);
    return;
  }

  // ② 诊断（轮播诊断短语）
  animMsg.textContent = 'AI 正在逐段分析你的简历…';
  startPhrases();

  let diagResult;
  try {
    diagResult = await diagnoseResume(uploadResult.resume_id);
  } catch (e) {
    stopPhrases();
    if (e.code === 409) {
      animMsg.textContent = '诊断进行中，请稍候…';
      startPhrases();
      // 409 说明已有诊断在处理中，等 3 秒后重试一次
      await new Promise(r => setTimeout(r, 3000));
      try {
        diagResult = await diagnoseResume(uploadResult.resume_id);
      } catch (e2) {
        stopPhrases();
        showRecover(`诊断失败：${e2.message}`);
        return;
      }
      stopPhrases();
    } else {
      showRecover(`诊断失败：${e.message}`);
      return;
    }
  }
  stopPhrases();

  // ③ MD5 命中 → 弹窗提示，不跳转
  if (diagResult.is_cached) {
    const confirmed = await showConfirm(
      '这份简历与上次上传的完全相同，无需重复诊断。是否查看上次诊断记录？',
      '查看记录',
      '重新上传'
    );
    if (confirmed) {
      sessionStorage.setItem('lastDiagnosisId', diagResult.diagnosis_id);
      sessionStorage.setItem('lastDiagnosisResult', JSON.stringify(diagResult));
      window.location.href = `diagnosis.html?diagnosis_id=${encodeURIComponent(diagResult.diagnosis_id)}`;
    } else {
      showRecover(null);
    }
    return;
  }

  // ④ 存 sessionStorage + 跳转
  sessionStorage.setItem('lastDiagnosisId', diagResult.diagnosis_id);
  sessionStorage.setItem('lastDiagnosisResult', JSON.stringify(diagResult));
  window.location.href = `diagnosis.html?diagnosis_id=${diagResult.diagnosis_id}`;
}

// ── 恢复 ────────────────────────────────────────────────

function showRecover(msg) {
  busy = false;
  uploadAnim.style.display = 'none';
  uploadZone.style.display = 'block';
  btnSubmit.style.display = 'block';
  if (msg) Toast.error(msg);
}

// ── 启动 ────────────────────────────────────────────────
// 登录态已在模块顶层初始化
