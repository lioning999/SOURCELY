/**
 * api/core.js — HTTP 客户端核心：callApi / token 管理 / 响应处理
 *
 * 所有 API 调用必须通过 callApi()，禁止页面直接使用 fetch。
 * localStorage key: accessToken（与 auth-callback.html 对齐）
 */

const TOKEN_KEY = 'accessToken';

// 同源部署：dev 和 prod 都是 FastAPI 挂载静态文件，无需跨域
const baseUrl = '';

// ── Token 管理 ──────────────────────────────────────────

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// ── 响应处理（私有）─────────────────────────────────────

/**
 * 解析响应。成功返回 JSON body；失败抛 Error。
 *
 * 后端两种返回格式：
 *   包装:   {code: 200|0, data: {...}, message: "ok"}
 *   不包装: {access_token, ...}  (/auth/*, /pay/create-order 等)
 *
 * 成功码: 200 或 0（/resume/upload 历史兼容）
 * 特殊码: 401=token过期, 402=次数不足, 409=防重冲突
 */
async function handleResponse(response) {
  const body = await response.json();

  // 成功: HTTP 2xx 且 (code 为 200/0 或无 code 字段)
  if (response.ok) {
    if (!body || typeof body !== 'object') return body;
    if (!('code' in body) || body.code === 200 || body.code === 0) return body;
  }

  // ── 错误处理 ──────────────────────────────
  if (response.status === 401) {
    clearToken();
    throw new Error('登录已过期，请重新登录');
  }

  // 402 = 频率/配额不足
  if (response.status === 402) {
    const err = new Error(body.message || '次数不足');
    err.quotaType = (body.data && body.data.quota_type) || null;
    err.code = 402;
    throw err;
  }

  // 409 = 防重冲突
  if (response.status === 409) {
    const err = new Error(body.message || '请求处理中，请勿重复提交');
    err.code = 409;
    throw err;
  }

  // 其他错误
  const msg = body.message || body.detail || `请求失败 (${response.status})`;
  throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
}

// ── 公开 API ───────────────────────────────────────────

/**
 * 统一 API 请求入口。
 *
 * @param {string} endpoint — 以 / 开头的 API 路径
 * @param {Object} options  — fetch 选项 (method, headers, body...)
 * @returns {Promise<any>}  — 解析后的响应 JSON
 */
export async function callApi(endpoint, options = {}) {
  if (!endpoint || !endpoint.startsWith('/')) {
    throw new Error('Endpoint 必须以 / 开头');
  }

  const token = getToken();
  const headers = { ...options.headers };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const resp = await fetch(baseUrl + endpoint, { ...options, headers });
  return handleResponse(resp);
}
