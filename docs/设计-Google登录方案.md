# Google 登录方案

> 生命周期：活跃 | 最后更新：2026-07-21

## 目录

1. [功能需求](#1-功能需求)
2. [技术架构](#2-技术架构)
3. [数据库](#3-数据库)
4. [API 接口](#4-api-接口)
5. [前端状态机](#5-前端状态机)
6. [安全边界](#6-安全边界)
7. [异常处理](#7-异常处理)
8. [V1 范围](#8-v1-范围)

---

## 1. 功能需求

### 用户故事
- **卖家**：我用 Google 账号登录，登录后可以收藏查看过的商品，下次回来能找到
- **卖家（未登录）**：不登录也能搜商品、看决策卡，但每天限 3 次
- **分享接收者**：别人分享给我的决策卡链接，我不需要登录就能看

### 登录时机

```
未登录 → 首页 → 搜商品 → 看结果（可看，不拦截）
  → 结果页轻提示："登入后可保存到我的商品，随时回看 →"
  → 点登录 → Google 弹窗 → 完成登录 → 自动保存当前结果

已登录 → 首页 → 搜商品 → 看结果 → 自动保存 → "历史"页可查
```

### 登录价值（用户视角）

| 状态 | 每日查询次数 | 历史记录 | 分享 |
|------|-------------|---------|------|
| 未登录 | 3 次/天 | ❌ | ✅ 可分享 |
| 已登录 | 不限 | ✅ "历史"页可查所有 | ✅ 可分享 |

---

## 2. 技术架构

### 整体流程

```
前端浏览器                          后端 FastAPI                     Google
─────────                          ────────────                     ──────

① 加载 Google SDK
   <script src="accounts.google.com/gsi/client" async defer>

② 渲染登录按钮 → 用户点击
   弹窗 → 选 Google 账号 → 同意授权

③ 收到 credential（JWT id_token）

④ POST /api/auth/google ──────────→
   { credential: "eyJ..." }
                                    ⑤ 验证 id_token ──────────────→
                                       google-auth.verify_oauth2_token()
                                    ←── {sub, email, name, picture}

                                    ⑥ upsert users 表
                                       WHERE google_id = sub

                                    ⑦ 签发自己的 JWT
                                       HS256, 7天过期

⑧ ←── { access_token, user }

⑨ sessionStorage.accessToken

⑩ 后续请求 Authorization: Bearer <access_token>
```

### 选型理由

| 选择 | 理由 |
|------|------|
| Google GIS SDK (`gsi/client`) | Google 2023 年新 SDK，替代旧版 `gapi.auth2`，移动端体验更好 |
| 前端拿 credential → 后端验证 | Google 推荐模式，不存 permanent token |
| 后端离线验证 | `google-auth` 库本地验签，比调 `tokeninfo` API 更快 |
| 自签 JWT (HS256, 7天) | 不暴露 Google token；7天过期不用 refresh |
| JWT 存 sessionStorage | 关标签即清除，比 localStorage 安全；V1 不需要 httpOnly Cookie |
| 单 Google 登录，不做邮箱密码 | 东南亚卖家都有 Gmail，一个登录方式最简 |

---

## 3. 数据库

### users 表

```sql
CREATE TABLE users (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  google_id   VARCHAR(100) NOT NULL UNIQUE,   -- Google 'sub' claim（唯一标识）
  email       VARCHAR(200),                   -- 可空（Google 账号可能无 email）
  name        VARCHAR(200),                   -- Google 账号显示名
  avatar_url  VARCHAR(500),                   -- Google 头像 URL
  created_at  DATETIME DEFAULT NOW(),
  last_login  DATETIME DEFAULT NOW()          -- 每次登录更新，用于清理僵尸用户
);
```

### 关联 analysis 表

```sql
ALTER TABLE analysis ADD user_id INT NOT NULL AFTER id;
ALTER TABLE analysis ADD FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE analysis ADD UNIQUE KEY uk_offer_user (offer_id, user_id);
```

---

## 4. API 接口

### POST /api/auth/google

登录 / 注册（自动判断）。

```
Request:
  Content-Type: application/json
  { "credential": "eyJh..." }          ← Google 返回的 id_token（JWT 格式）

验证:
  payload = verify_oauth2_token(
      credential, Request(), CLIENT_ID,
      clock_skew_in_seconds=60
  )

验证清单:
  ✅ aud == CLIENT_ID                  ← 防止 token 被重放到其他应用
  ✅ exp > now                         ← Google token 有效期为 1 小时
  ✅ iss in ('accounts.google.com', 'https://accounts.google.com')

业务逻辑:
  1. google_id = payload.sub
  2. SELECT FROM users WHERE google_id = google_id
  3. 无记录 → INSERT；有记录 → UPDATE name, avatar_url, last_login
  4. 签发 JWT（自签，HS256，7天过期）
  5. 返回 access_token + user

Response 200:
  {
    "access_token": "eyJ...",
    "user": {
      "id": 1,
      "name": "Nguyen Van A",
      "email": "nguyenvana@gmail.com",
      "avatar_url": "https://lh3.googleusercontent.com/..."
    }
  }

Response 400:
  { "detail": "登录失败：Google 验证未通过" }
```

### JWT 签发参数

```python
access_token = jwt.encode({
    "user_id": user.id,
    "email": user.email,
    "exp": datetime.utcnow() + timedelta(days=7),
    "iat": datetime.utcnow(),
}, JWT_SECRET, algorithm="HS256")
```

| 参数 | 值 | 说明 |
|------|-----|------|
| algorithm | HS256 | 单进程够用，不需要非对称 |
| exp | 7 天 | 无敏感操作，到期重登 |
| refresh | ❌ 不做 | V1 不需要 |

### JWT 验证中间件

所有需要登录的接口（如 `POST /api/analysis`），通过中间件统一验证：

```python
# middleware.py
async def jwt_middleware(request, call_next):
    if request.url.path in PUBLIC_PATHS:  # ['/api/auth/google', '/api/report/']
        return await call_next(request)

    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '')
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        request.state.user_id = payload['user_id']
        request.state.email = payload['email']
    except:
        return JSONResponse({'detail': '请先登录'}, status_code=401)

    return await call_next(request)
```

### 公开路径（无需登录）

| 路径 | 说明 |
|------|------|
| `GET /` | 首页 |
| `GET /report.html` | 分析页 |
| `GET /api/report/{offer_id}` | 公开分享的决策卡数据 |
| `POST /api/auth/google` | 登录接口 |
| `GET /static/*` | 静态资源 |

---

## 5. 前端状态机

### 页面生命周期

```
页面加载
  ├─ Google SDK 异步加载（async defer，不阻塞渲染）
  ├─ renderNav()         → 渲染 nav 骨架
  ├─ checkAuth()         → 检查 sessionStorage 中的 JWT
  │   ├─ 已登录         → nav 改为头像模式
  │   └─ 未登录/JWT过期 → nav 显示登录按钮
  └─ initGoogleLogin()   → Google SDK 加载完毕后挂载登录按钮

并行加载，互不阻塞。页面先渲染，登录可选。
```

### Nav 两种状态

```
未登录态:
┌───────────────────────────────────────┐
│ 源采 SOURCELY   首页  分析  [Google 登入] │
└───────────────────────────────────────┘

已登录态:
┌───────────────────────────────────────┐
│ 源采 SOURCELY   首页  分析  历史  [👤] │
└───────────────────────────────────────┘
```

### 前端 JS 关键代码

```js
// 初始化 Google 按钮
function initGoogleLogin() {
  google.accounts.id.initialize({
    client_id: CLIENT_ID,
    callback: handleCredential,
    auto_select: false,             // 不自动弹窗，用户手动点
    cancel_on_tap_outside: true,
  });
  google.accounts.id.renderButton(
    document.getElementById('googleBtn'),
    { theme: 'outline', size: 'large', text: 'signin_with', width: 180 }
  );
}

// Google 返回 credential → 发给后端
async function handleCredential(response) {
  const res = await fetch('/api/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential: response.credential })
  });
  if (!res.ok) { alert('登录失败，请重试'); return; }
  const { access_token, user } = await res.json();
  sessionStorage.setItem('accessToken', access_token);
  sessionStorage.setItem('user', JSON.stringify(user));
  location.reload();  // 刷新让 nav 变成已登录态
}

// 检查当前登录态
function checkAuth() {
  const token = sessionStorage.getItem('accessToken');
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    if (payload.exp * 1000 < Date.now()) {
      sessionStorage.removeItem('accessToken');
      sessionStorage.removeItem('user');
      return null;
    }
    return JSON.parse(sessionStorage.getItem('user'));
  } catch(e) { return null; }
}

// 退出登录
function logout() {
  sessionStorage.removeItem('accessToken');
  sessionStorage.removeItem('user');
  google.accounts.id.disableAutoSelect();
  location.reload();
}
```

### Google 按钮样式

- 使用 Google 官方 `renderButton`（不允许自定义替代，用户靠识别 G 图标建立信任）
- 主题：`outline`（白底灰边框 + 彩色 G 图标）
- 尺寸：`large`（高度 44px，满足最小触控区域）
- 宽度：`180px`（适配移动端 nav 空间）
- 登录后：按钮替换为头像小圆图（28×28）+ 点击可退出

---

## 6. 安全边界

| 攻击面 | 防御 |
|--------|------|
| ID token 被篡改 | Google 签名验证，篡改直接抛异常 |
| ID token 重放（跨应用） | 验证 `aud` = 本应用 CLIENT_ID |
| ID token 过期 | 验证 `exp`，超时拒绝（Google token 1 小时有效） |
| JWT 泄露（XSS） | 存 sessionStorage 非 localStorage；关标签即清；HTTPS 传输 |
| CSRF | JWT 放 `Authorization: Bearer` Header，非 Cookie，天然免疫 |
| XSS 偷 credential | Cookie 不做凭证存储；CSP header 限制 script-src |
| Google SDK 加载失败 | 降级：所有功能仍可用，只是不能登录 |
| 共用设备残留 | sessionStorage 关标签清除；`logout()` 手动清除 |

---

## 7. 异常处理

| 场景 | 前端表现 | 后端行为 |
|------|---------|---------|
| Google SDK 加载超时（>5s） | Nav 不显示登录按钮，页面正常使用 | — |
| 用户关闭 Google 弹窗 | 无反应，停留当前页 | — |
| Google token 过期（>1h） | "登录超时，请重新登录" | 返回 400 |
| Google token 验证失败 | "登录失败，请重试" | 返回 400 + detail |
| 后端 JWT 过期（>7d） | 清 token，nav 恢复未登录态 | 返回 401 |
| JWT 被篡改 | 清 token，nav 恢复未登录态 | 返回 401（decode 抛出） |
| 用户重复登录（已登录再点） | 覆盖旧 token，更新 last_login | upsert user |
| Google 账号无 email | 正常登录，email=NULL | 允许 email 可空 |
| 网络错误 | "网络错误，请检查网络后重试" | — |
| 服务端错误 | "服务器错误，请稍后重试" | 返回 500 |

### 降级

**最坏情况：** Google OAuth 应用被封 → 所有用户无法登录。

**恢复路径：** `users` 表有 `email` 字段 → 临时切"邮箱 + 验证码"登录（V1 不做，架构已预留）。

---

## 8. V1 范围

### 做

| 功能 | 说明 |
|------|------|
| ✅ Google OAuth 2.0 登录 | 唯一登录方式，Google GIS SDK |
| ✅ 自动注册 | 首次登录自动创建用户 |
| ✅ JWT 签发 + 验证 | HS256，7 天过期，中间件验证 |
| ✅ Nav 两种状态 | 未登录（登录按钮）/ 已登录（头像 + 历史） |
| ✅ 退出登录 | 清除 token + Google disableAutoSelect |
| ✅ sessionStorage 存储 | 关标签即清除 |
| ✅ 未登录查询限制 | 3 次/天（sessionStorage 计数） |
| ✅ "历史"页面 | 登录后可见，列出查过的商品 |

### 不做

| 功能 | 理由 |
|------|------|
| ❌ Refresh Token | 7 天过期重登，无敏感操作 |
| ❌ 邮箱密码登录 | Google = 唯一方式，最简 |
| ❌ 多设备同步 | 无实时需求 |
| ❌ 权限/角色 | 所有用户平等 |
| ❌ 注销/删除账号 | V2 |
| ❌ httpOnly Cookie | V1 复杂度不划算 |
| ❌ 后端 session | 无状态 JWT 更简单 |
