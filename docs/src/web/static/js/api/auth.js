/**
 * api/auth.js — 认证相关 API：code 换 token + 用户信息
 */
import { callApi, setToken, clearToken } from './core.js';

/**
 * 用微信授权码换取 JWT，自动存储 token。
 * @param {string} code — 微信 OAuth 回调传来的 code
 * @returns {Promise<{access_token, token_type}>}
 */
export async function exchangeAuthCode(code) {
  const data = await callApi('/auth/exchange', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });

  if (!data.access_token) {
    throw new Error('登录失败：未收到有效的访问令牌');
  }

  setToken(data.access_token);
  return data;
}

/**
 * 获取当前用户信息（需已登录）。
 * @returns {Promise<object>}
 */
export async function getQuota() {
  const data = await callApi('/auth/info');
  return data;
}

/**
 * 清除登录态。
 */
export function logout() {
  clearToken();
}
