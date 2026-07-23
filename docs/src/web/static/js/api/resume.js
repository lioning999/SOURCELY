/**
 * api/resume.js — 简历相关 API：上传 / 诊断 / 预览 / 结果 / 追问预判
 */
import { callApi } from './core.js';

// ── 上传 ───────────────────────────────────────────────

/**
 * 上传简历文件，提取文本。
 * @param {File} file — PDF / DOCX / TXT 文件
 * @returns {Promise<{resume_id, filename, file_size, text_length}>}
 */
export async function uploadResume(file) {
  if (!(file instanceof File)) throw new Error('必须是 File 类型');

  const formData = new FormData();
  formData.append('file', file);

  // 不设 Content-Type — 浏览器自动带 multipart/form-data + boundary
  const result = await callApi('/resume/upload', {
    method: 'POST',
    body: formData,
  });

  return result.data;
}

// ── 诊断 ───────────────────────────────────────────────

/**
 * AI 诊断简历。同用户同 resume_id 并发请求返回 409。
 * @param {string} resumeId — 简历 UUID
 * @returns {Promise<{diagnosis_id, overall_impression, fatal_issues, is_cached?, is_rediagnosis?}>}
 */
export async function diagnoseResume(resumeId) {
  if (!resumeId) throw new Error('resumeId 不能为空');

  const result = await callApi('/resume/diagnose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_id: resumeId }),
  });

  // 后端将 AI 输出嵌套在 result 字段下，打平供前端使用
  const data = result.data;
  if (data && data.result) {
    const inner = data.result;
    delete data.result;
    Object.assign(data, inner);
  }
  return data;
}

// ── 优化预览 ───────────────────────────────────────────

/**
 * AI 全文优化 + 入库，返回 Top 2 before/after 对比。
 * 幂等：已有优化结果时直接返回缓存（data.cached = true）。
 * @param {string} diagnosisId — 诊断 UUID
 * @returns {Promise<{preview, total_issues, diagnosis_id, cached?}>}
 */
export async function previewResume(diagnosisId) {
  if (!diagnosisId) throw new Error('diagnosisId 不能为空');

  const result = await callApi('/resume/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ diagnosis_id: diagnosisId }),
  });

  return result.data;
}

// ── 获取已有诊断 ───────────────────────────────────────

/**
 * 按 ID 获取已有诊断数据（用于首页记录跳转、刷新恢复等场景）。
 * @param {string} diagnosisId — 诊断 UUID
 * @returns {Promise<Object>} — 打平后的诊断结果（含 overall_impression, fatal_issues, is_paid 等）
 */
export async function getDiagnosis(diagnosisId) {
  if (!diagnosisId) throw new Error('diagnosisId 不能为空');

  const result = await callApi(`/resume/diagnosis?diagnosis_id=${encodeURIComponent(diagnosisId)}`);

  return result.data;
}

// ── 获取优化结果 ───────────────────────────────────────

/**
 * 从 DB 读取优化全文 + before/after 对比 + 追问预判（如已生成）。
 * 纯读取，次数在 preview 时已扣。未优化时返回 400。
 * @param {string} diagnosisId — 诊断 UUID
 * @returns {Promise<{optimized_text, before_after_pairs, diagnose_summary, interview_qa, diagnosis_id}>}
 */
export async function getOptimizeResult(diagnosisId) {
  if (!diagnosisId) throw new Error('diagnosisId 不能为空');

  const result = await callApi(`/resume/result?diagnosis_id=${encodeURIComponent(diagnosisId)}`);

  return result.data;
}
