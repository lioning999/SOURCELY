# API 后端框架护栏

> Layer 2 — Python/FastAPI 专属约束。AI 写任何 Python 代码前必须先读本文件。
> 最后更新：2026-07-21 — Sourcely V1（Google OAuth + Apify + 零 AI 规则引擎）

## 一、架构边界（铁律）

```
请求 → CORS → JWT 中间件 → routes/（Pydantic 参数校验）
       → services/（业务逻辑编排）
         → adapters/（外部 API — Google OAuth / Apify）
         → repositories/（数据库操作 — 连接生命周期封装）
         → domain/（纯逻辑 — 规则引擎 / 缓存）
```

| 层 | 职责 | 禁止 |
|----|------|------|
| **routes/** | Pydantic 参数校验 + 调用 service + 返回标准响应 | 直接操作数据库、包含业务逻辑、直接调外部 API |
| **services/** | 业务逻辑编排，注入 adapter + repository | 手写 SQL、手管数据库连接、raise HTTPException |
| **adapters/** | 外部 API 封装（Google OAuth、Apify 1688 Scraper）。一个外部服务一个文件 | 包含业务逻辑、操作数据库 |
| **repositories/** | 数据库操作封装。连接生命周期自管 | 包含业务逻辑、调外部 API |
| **domain/** | 纯函数，零外部依赖。规则引擎、缓存、判词计算 | 调数据库、调 API、读环境变量 |
| **utils/** | 纯工具函数（异常/JWT/日志） | 依赖 services/ 或 routes/ |

**越层调用 = 违宪。** 发现 PR 直接拒绝。

同层不互调：`service_a.py` 不能调 `service_b.py`，公共逻辑提取到 domain/。

API 路径不使用 `/api/v1/` 前缀。

**文件行数上限：每个文件 ≤ 200 行。** Service 层一个方法 ≤ 50 行。

## 二、Python 代码规范

- PEP8，4 空格缩进
- **所有函数必须有完整类型注解（参数 + 返回值）**
- 异步边界在签名中可见：`async` / `await` 不能漏
- import 放文件顶部，禁止函数体内 import（除非循环引用且注释说明）

## 三、命名一致性

| 类型 | 规范 | 示例 |
|------|------|------|
| Routes 文件 | `routes/{资源}.py` | `routes/auth.py` |
| Services 文件 | `services/{资源}_svc.py` | `services/auth_svc.py` |
| Repositories 文件 | `repositories/{表名}_repo.py` | `repositories/user_repo.py` |
| Adapters 文件 | `adapters/{服务名}.py` | `adapters/google_auth.py` |
| Domain 文件 | `domain/{功能}.py` | `domain/verdict_engine.py` |
| 函数名 | 动词 + 名词 | `create_token()`、`get_by_google_id()` |
| 前端 sessionStorage key | camelCase | `accessToken`、`user` |

## 四、响应格式

**标准统一：** `{code: 200, data: ..., message: "ok"}` — code 值 = HTTP 状态码

| 场景 | 格式 |
|------|------|
| 正常返回 | `{code: 200, data: {...}, message: "ok"}` |
| 错误返回 | `{code: 4xx/5xx, data: null, message: "错误描述"}` |
| 登录回调 | `RedirectResponse`（302 重定向到首页带 token） |

**禁止：** 同一个项目出现两种响应格式。

## 五、认证中间件

```
CORS（最外层，OPTIONS 放行）→ JWT（内层，Bearer token 校验）
```

- **认证方式：** Google OAuth 2.0 + 自签 JWT（HS256，7 天过期）
- **用户身份注入：** `request.state.user_id`
- **PROTECTED_PREFIXES + EXEMPT_PATHS 模式：**
  - `PROTECTED_PREFIXES = ["/api/"]` — 需 JWT 认证
  - `EXEMPT_PATHS = ["/api/auth/google/login", "/google-callback", "/docs", "/openapi.json", "/health"]` — 保护前缀下的免认证路径
  - 不在前缀内的路径（`/` 前端静态文件等）默认放行
- Token 透传：`Authorization: Bearer <token>`
- 中间件返回 JSONResponse，不抛异常（抛异常被 Starlette 转 500）
- **用户身份从 `request.state.user_id` 获取，禁止前端传入 user_id**

### Google 登录（服务端 OAuth 2.0 流程）

- Client ID / Secret：`.env` 中 `OAuth_CLIENT_ID` + `OAuth_CLIENT_SECRET`
- Redirect URI：`http://localhost:8008/google-callback`
- 流程：
  1. `GET /api/auth/google/login` → 302 重定向到 Google 授权页
  2. 用户授权 → Google 回调 `GET /google-callback?code=xxx`
  3. 后端 code 换 id_token（调 Google token 端点）
  4. `google-auth` 离线验证 id_token（aud / exp / iss）
  5. Upsert users 表 → 签发自签 JWT
  6. 302 重定向首页，token 通过 URL query 传递
- 前端 token 存 `sessionStorage`（非 `localStorage`），关闭标签页即清除

## 六、数据库

- **MySQL 8.0**，字符集 `utf8mb4`，引擎 InnoDB，连接池 5-20（aiomysql 异步）
- **库名：** `sourcely_DB`（与 `.env` `DATABASE_NAME` 一致）
- **autocommit=False（铁律）**：连接池必须设 `autocommit=False`，事务由 Repository 层显式 commit/rollback
- **SQL 100% 参数化（`%s`）**，动态字段名用白名单校验
- **DictCursor（铁律）**：`conn.cursor(aiomysql.DictCursor)` 返回 dict，不返回 tuple
- **表结构以 `db/schema.sql` 为准**，CLAUDE.md 不存 DDL

### Sourcely 表结构（5 张表）

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `users` | Google 登录用户 | id, google_id(UNIQUE), email, name, avatar_url |
| `analysis` | 商品分析记录 | id, user_id(FK), offer_id, status, 价格/店铺/判词 |
| `analysis_spec` | 规格参数 (1:N) | analysis_id(FK CASCADE), spec_key, spec_value |
| `analysis_sku` | SKU 变体 (1:N) | analysis_id(FK CASCADE), sku_name, sku_image |
| `analysis_price_tier` | 阶梯价格 (1:N) | analysis_id(FK CASCADE), qty_min, qty_max, unit_price |

- `analysis` 表 `offer_id + user_id` 联合唯一：同一用户不重复分析同一商品
- 子表全部 `ON DELETE CASCADE`
- `analysis.status`: `pending → running → done/failed`

## 七、Repository 层（数据库操作封装）

一个 repository 文件对应一张表。Service 层不手写 SQL、不管连接生命周期。

```python
# repositories/user_repo.py — 标准形状
import aiomysql
from database import AsyncDatabaseConnection

class UserRepository:
    """users 表 CRUD。事务由 service 层控制。"""

    async def get_by_google_id(self, google_id: str) -> dict[str, Any] | None:
        conn = await AsyncDatabaseConnection.get_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT id, google_id, email, name, avatar_url, created_at, last_login FROM users WHERE google_id=%s",
                    (google_id,),
                )
                return await cur.fetchone()
        finally:
            await AsyncDatabaseConnection.close_connection(conn)

    async def create(self, google_id: str, email: str | None = None, ...) -> int:
        conn = await AsyncDatabaseConnection.get_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("INSERT INTO users (...) VALUES (%s, %s, ...)", (...))
                await conn.commit()
                return cur.lastrowid
        except Exception:
            await conn.rollback()
            raise
        finally:
            await AsyncDatabaseConnection.close_connection(conn)
```

规则：
- 一个 repository 文件对应一张数据库表
- 每个方法自管连接（get → try → commit/rollback → finally close）
- 使用 `aiomysql.DictCursor`，返回 dict 或 None
- 不包含业务逻辑，不调外部 API
- 方法名：`get_` / `create_` / `update_` / `delete_` / `count_` / `exists_`

## 八、Adapter 层（外部 API 封装）

所有外部 HTTP 调用集中在此。一个外部服务一个文件。

```python
# adapters/google_auth.py — 标准形状
class GoogleAuthAdapter:
    """Google OAuth 2.0 服务端流程适配器。"""

    def get_auth_url(self) -> str: ...

    async def exchange_code(self, code: str) -> dict:
        """code 换 id_token → 验证 → 返回 payload。
        异常包装为 ExternalServiceError。"""
        ...
```

规则：
- `adapters/google_auth.py` — Google OAuth 2.0
- `adapters/apify.py` — Apify 1688 Wholesale Scraper
- Adapter 不包含业务逻辑，不操作数据库
- 所有外部异常包装为 `ExternalServiceError`
- 超时和重试策略在 adapter 内实现
- 模块级单例：`google_auth_adapter = GoogleAuthAdapter()`

## 九、Domain 层（纯逻辑）

零外部依赖的纯函数。输入 → 计算 → 输出。

```
domain/
├── cache.py           # 内存缓存（offer_id → 结果，TTL 30min，LRU 淘汰）
├── verdict_engine.py  # V1 规则引擎（L1+L2+L3 三层判词）
└── rate_limiter.py    # 滑动窗口全局限流（30 次/分钟）
```

规则：
- 不 import 数据库模块、HTTP 客户端、FastAPI 类型
- 不读环境变量、不读文件系统
- 纯函数：相同输入永远相同输出
- 可单测：不需要 mock 任何东西

## 十、异常体系

10 种异常类（`utils/exceptions.py`）：
`AppError`（基类）→ `ValidationError`(400) / `AuthenticationError`(401) / `AuthorizationError`(403) / `ResourceNotFoundError`(404) / `OptimisticLockError`(409) / `ExternalServiceError`(502) / `ServiceUnavailableError`(503) / `DatabaseError`(500) / `InsufficientQuotaError`(403)

全局异常处理器自动转换 `AppError` → `{code, data, message}`。

### services/ 层异常铁律

| 场景 | 用哪个异常 |
|------|-----------|
| 参数校验失败 | `raise ValidationError(...)` |
| 资源不存在 | `raise ResourceNotFoundError(...)` |
| DB 操作失败 | `raise DatabaseError(...)` |
| 外部服务挂了 | `raise ExternalServiceError(...)` |
| **永远不要** | `raise HTTPException` / `raise ValueError` |

### 异常透传（铁律）

**Adapter 已抛 AppError 子类时，Service 层透传，禁止重新包装。**

```python
# ✅ 正确
try:
    result = await self.adapter.exchange_code(code)
except ExternalServiceError:
    raise  # Adapter 已包装，原样透传

# ❌ 错误
try:
    result = await self.adapter.exchange_code(code)
except Exception:
    raise ExternalServiceError(service_name="Google")  # 丢失原始错误
```

## 十一、Apify 集成

- **Actor：** `zen-studio/1688-wholesale-scraper`（Zen Studio 官方）
- **模式：** 启动 run → 轮询 dataset → 返回结果（异步轮询，非阻塞等待）
- **超时：** 90 秒（覆盖 95% 正常情况）
- **降级：** 超时后有缓存返回缓存 + "数据可能不是最新"；无缓存返回明确错误
- **成本控制：** offer_id 缓存 30min TTL + 全局限流 30 次/分钟
- **Apify 调用期间必须释放 DB 连接**

## 十二、V1 零 AI（铁律）

**V1 不使用任何大语言模型。判词用纯规则引擎，翻译用手动模板。**
禁止引入 `openai`、`anthropic`、任何 LLM SDK。

## 十三、路由层并发控制（铁律）

**对同一资源的并发写请求，路由层必须加轻量防重。**

```python
_pending: dict[str, asyncio.Event] = {}

@router.post("/xxx")
async def handler(request, body):
    key = f"{request.state.user_id}:{业务唯一标识}"
    if key in _pending:
        return JSONResponse(status_code=409, content={"code": 409, "message": "请求处理中"})
    done = asyncio.Event()
    _pending[key] = done
    try:
        result = await service.do_work(...)
        return result
    finally:
        done.set()
        _pending.pop(key, None)
```

**禁止：** `SELECT COUNT` → `INSERT` 两步模式做幂等——并发下必出竞态。

## 十四、全局资源清理（铁律）

| 资源类型 | 清理方式 |
|---------|---------|
| 数据库连接池 | 应用关闭时 `close_pool()`（main.py lifespan） |
| 全局 dict 缓存 | 必须有大小上限 + LRU 淘汰 |
| `asyncio.Task` | 创建前先 cancel 旧任务 |

违反后果：hot-reload 每次重载泄漏连接；无上限缓存 OOM。

## 十五、安全底线

- 密钥从环境变量读取，缺失启动报错（`Config.validate()`）
- `.env` 不提交 Git，`.env.example` 可提交（不含真实值）
- 用户身份从 `request.state.user_id` 获取，**禁止前端传入 user_id**
- **任何业务判断（数据归属、付费状态）必须后端独立校验**
- Google id_token 验证清单：`aud == CLIENT_ID` + `exp > now` + `iss in ('accounts.google.com', 'https://accounts.google.com')`
- Token 禁止进日志、禁止进响应体（除登录接口外）

## 十六、日志规范

- 文件轮转 + 控制台双输出（`utils/logger.py`）
- 脱敏：email 前 3 位 + `***@***`，token 只记长度
- **级别规范：**
  | 级别 | 场景 |
  |------|------|
  | `info` | 登录/注册、Apify 任务状态变化、关键业务节点 |
  | `warning` | 可恢复异常（连接断开重连、轮询重试） |
  | `error` | 需人工介入（Google 验证失败、DB 连接池创建失败） |
  | `debug` | JWT 验签、DB 连接获取/释放 |

## 十七、配置与构建

```bash
# 后端
cd src/api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8008

# 前端（开发时通过 FastAPI 访问，已挂载 src/web/ 为静态文件）
# 访问 http://localhost:8008
```

### 环境变量加载

- **`load_dotenv` 只在 `config.py` 调用一次。** 其他模块从 `config.Config` 读配置
- 代码中引用常量：`Config.GOOGLE_CLIENT_ID`，不写死值
- `config.py` 的默认值必须与 `.env.example` 中对应条目一致
- 新增配置项必须同时在 `config.py` 和 `.env.example` 两处添加
- 密钥缺失启动报错（`Config.validate()`），禁止带病启动

## 十八、资源约束速查

| 约束项 | 值 | 位置 |
|--------|-----|------|
| 数据库连接池 | 5-20 | `database.py` |
| JWT 有效期 | 7 天（1440 min） | `.env` `JWT_EXPIRE_MINUTES` |
| Google OAuth Redirect | `http://localhost:8008/google-callback` | `.env` `OAuth_REDIRECT_URI` |
| Apify 等待超时 | 90 秒 | `config.py` `APIFY_WAIT_SECONDS` |
| 分析缓存 TTL | 30 分钟 | `domain/cache.py` |
| 全局限流 | 30 次/分钟 | `domain/rate_limiter.py` |
| 缓存上限 | 500 条 | `domain/cache.py` |
| 每日免费分析次数 | 不限（V1 全免费） | — |

## 十九、死代码清理（铁律）

**删除任何函数/类/变量前，必须 grep 全项目所有引用点。** 确认零引用后才能删除。

## 二十、测试

- 修改模块后必须运行对应测试，全部通过才能提交
- 所有测试文件放 `tests/`，按层分子目录
- 测试原则：测行为不测实现，一条测试一个断言，mock 外部依赖
- Adapter 层测试用 MockAdapter
- Repository 层测试用测试数据库
- Domain 层测试不需要任何 mock
- Service 层测试组合 MockAdapter + MockRepository
