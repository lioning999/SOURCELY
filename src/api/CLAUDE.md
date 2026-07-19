# API 后端框架护栏
> Layer 2 — Python/FastAPI 专属约束。AI 写任何 Python 代码前必须先读本文件。
>
> 适用：中轻量级 Python 项目（FastAPI + MySQL/PostgreSQL）

## 一、架构边界（铁律）
```
请求 → CORS → JWT中间件 → routes/（参数校验）
       → services/（业务逻辑编排）
         → adapters/（外部 API 调用）
         → repositories/（数据库操作）
         → domain/（纯逻辑）
```
| 层 | 职责 | 禁止 |
|----|------|------|
| **routes/** | Pydantic 参数校验 + 调用 service + 返回标准响应 | 直接操作数据库、包含业务逻辑、直接调外部 API |
| **services/** | 业务逻辑编排，注入 adapter + repository | 手写 SQL、手管数据库连接、raise HTTPException |
| **adapters/** | 外部 API 封装。一个外部服务一个文件 | 包含业务逻辑、操作数据库 |
| **repositories/** | 数据库操作封装。连接生命周期自管 | 包含业务逻辑、调外部 API |
| **domain/** | 纯函数，零外部依赖 | 调数据库、调 API、读环境变量 |
| **utils/** | 纯工具函数（异常/JWT/日志） | 依赖 services/ 或 routes/ |
**越层调用 = 违宪。** 发现 PR 直接拒绝。

## 二、Python 代码规范
- PEP8，4 空格缩进
- **所有函数必须有完整类型注解（参数 + 返回值）**
- 异步边界在签名中可见：`async` / `await` 不能漏
- import 放文件顶部，禁止函数体内 import（除非循环引用且注释说明）

## 三、命名一致性
- 文件名跨层对齐：`routes/auth.py` ↔ `services/auth.py` ↔ `repositories/users.py`
- 函数名动词+名词：`create_user()`、`get_order_by_id()`
- 一个文件对应一个资源/一张表，不混用

## 四、响应格式
**标准：** `{code: 200, data: ..., message: "ok"}` — code 值 = HTTP 状态码
| 场景 | 格式 |
|------|------|
| 正常返回 | `{code: 200, data: {...}, message: "ok"}` |
| 错误返回 | `{code: 4xx/5xx, data: null, message: "错误描述"}` |
| 特殊（如登录） | `{access_token, token_type}` — 不包装 |
**禁止：** 同一个项目出现两种响应格式。DeepSeek容易每个接口发明一种返回——发现立即修复。

## 五、异常体系

### 使用规则
| 场景 | 异常类 | 谁处理 |
|------|--------|--------|
| 参数校验失败 | `raise ValidationError(...)` | 全局异常处理器 → JSON |
| 资源不存在 | `raise ResourceNotFoundError(...)` | 同上 |
| DB 操作失败 | `raise DatabaseError(...)` | 同上 |
| 外部服务挂了 | `raise ExternalServiceError(...)` | 同上 |
| **Service 层禁止** | `raise HTTPException` / `raise ValueError` | — |

### 异常透传（铁律）
**Adapter 已抛 AppError 时，Service 层必须透传，禁止重新包装。**
```python
# ✅ 正确：AppError 原样透传
try:
    result = await self.adapter.call()
except ExternalServiceError:
    raise   # 已包装好，透传
except Exception as e:
    raise ExternalServiceError(service_name="XX") from e

# ❌ 错误：把已有错误包了第二层
try:
    result = await self.adapter.call()
except Exception:
    raise ExternalServiceError(service_name="XX")  # 丢了原始错误
```

## 六、路由层并发控制（铁律）
**对同一资源的并发写请求，路由层必须加轻量防重。** 防止用户快速双击或重试导致重复操作。
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

## 七、全局资源清理（铁律）
**任何模块级全局资源必须有对应的清理机制。**
| 资源类型 | 清理方式 |
|---------|---------|
| 数据库连接池 | 应用关闭时 `close_pool()` |
| 线程池 | `atexit.register(pool.shutdown)` |
| 全局 dict 缓存 | 必须有大小上限 + TTL 或 LRU 淘汰 |
| 后台 Task | 创建前先 cancel 旧任务 |
**违反后果：** hot-reload 每次重载泄漏一个资源；无上限缓存 OOM。

## 八、数据库约束
> 数据库选型与连接管理。重要信息和性能规则。

### 8.1 技术选型
- **MySQL 8.0**，字符集 `utf8mb4`，引擎 InnoDB
- 连接池大小 5-20，使用 **aiomysql** 异步驱动

### 8.2 事务管理（铁律）
**连接池必须设 `autocommit=False`。** Repository 层显式 commit/rollback，禁止设为 True。
```python
# ✅ 正确
async def create(self, data):
    async with self.conn.cursor() as cur:
        await cur.execute("INSERT ...", data)
        await self.conn.commit()

# ❌ autocommit=True → commit/rollback 全部空操作
# INSERT 无法回滚，支付模块事务安全彻底失效
```

### 8.3 SQL 安全
- **SQL 100% 参数化（`%s`）**，禁止字符串拼接
- 动态字段名用白名单校验，禁止直接拼接列名
- 复杂查询优先写视图或存储过程，不在代码中拼动态 SQL

### 8.4 AI 调用连接释放
AI 调用期间必须释放数据库连接回到连接池，避免长占用耗尽连接：
```
预检查 → commit → close → 调 AI → 重连 → 后续写入
```
禁止在 AI 等待响应期间持有数据库连接。

### 8.5 表结构管理
- **表结构以 `db/schema.sql` 为准**，CLAUDE.md 不存 DDL
- 新增字段/表，先改 `schema.sql`，再改 Repository
- `schema.sql` 纳入版本管理，执行前人工 review

## 九、配置与环境变量
- **`load_dotenv` 只在 `config.py` 调用一次。** 其他模块从 `Config` 读配置
- 代码中引用常量：`Config.SOME_KEY`，不写死值
- `config.py` 的默认值必须与 `.env.example` 中对应条目一致
- 新增配置项必须同时在 `config.py` 和 `.env.example` 两处添加
- 密钥缺失启动报错（`Config.validate()`），禁止带病启动

## 十、安全铁律（冗余提醒）
> 以下 3 条在架构宪法中已有，此处重复强化。对 DeepSeek 的必要策略。
1. **用户身份从 `request.state` 获取，禁止前端传入**
2. **SQL 100% 参数化（`%s`），动态字段名用白名单校验**
3. **密钥从 `.env` → `Config` 读取，禁止硬编码**

## 十一、日志规范

### 级别规则
| 级别 | 场景 | 禁止 |
|------|------|------|
| `info` | 关键节点 | — |
| `warning` | 可恢复异常 | — |
| `error` | 需人工介入 | 吞异常不记录 |
| `debug` | 开发调试 | 上生产 |

### 铁律
1. **生产代码零 `print()`**（CLI 工具除外）
2. **敏感数据脱敏**后记录，只显后 4 位
3. **异常日志必带上下文**（用户 ID、资源 ID、操作类型）
4. **禁止日志中写入**密钥、Token、完整密码

## 十二、依赖管理
1. **新增依赖先写 `requirements.txt`，再写代码 import**——禁止反序
2. 可选依赖用注释标记 `# 按需`，不混入主依赖区
3. 禁止引入 `requirements.txt` 之外的包。需要先加文件再 import
4. 本地开发临时依赖（jupyter、ipdb）不提交
