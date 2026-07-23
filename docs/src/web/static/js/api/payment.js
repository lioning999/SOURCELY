/**
 * api/payment.js — 支付相关 API：创建订单 / 查询状态
 */
import { callApi } from './core.js';

/**
 * 创建微信支付订单。
 * @param {number} plan — 1=打赏(¥1/次)
 * @param {string|null} diagnosisId — 关联诊断ID，用于付费后解锁
 * @returns {Promise<{qr_code_url, out_trade_no, amount, plan}>}
 */
export async function createOrder(plan, diagnosisId = null) {
  if (plan !== 1 && plan !== 2) throw new Error('套餐类型仅支持 1 或 2');

  const body = { plan };
  if (diagnosisId) body.diagnosis_id = diagnosisId;

  const data = await callApi('/pay/create-order', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  return data;
}

/**
 * 查询订单支付状态（前端轮询用，间隔 ≥3 秒）。
 * @param {string} outTradeNo — 商户订单号
 * @returns {Promise<{status: 'pending'|'paid', out_trade_no: string}>}
 */
export async function queryOrder(outTradeNo) {
  if (!outTradeNo) throw new Error('订单号不能为空');

  const data = await callApi(`/pay/order-status/${encodeURIComponent(outTradeNo)}`);

  return data;
}
