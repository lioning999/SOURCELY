# Admin 管理后台框架护栏

> Layer 2 — 管理后台代码约束。AI 写 admin 代码前必须先读本文件。
>
> **行数：~50 行**

---

## 定位

管理后台与主站物理隔离：

- 独立 HTML 页面，不引用主站组件
- 独立 API 调用封装（`static/js/api.js`）
- 独立 JWT token（`admin_token`，存 `sessionStorage`）

## 认证

| 维度 | 约束 |
|------|------|
| 鉴权方式 | 独立于用户 JWT，自带 `Depends(verify_admin_token)` |
| Token key | `admin_token`（非 `accessToken`） |
| 存储 | `sessionStorage` |
| 权限粒度 | 按需设计，不套用户权限体系 |

## 禁止事项

| 禁止 | 原因 |
|------|------|
| ❌ 使用主站的 API 封装 | 鉴权完全独立 |
| ❌ 暴露用户敏感信息 | 日志脱敏、响应脱敏 |
| ❌ 直接操作核心业务数据 | 必须走主站 Service 层 |
