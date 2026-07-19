# AI Code Kit

> 针对 DeepSeek 用户的 AI 编程约束体系——项目骨架 + 三层宪法 + skills，让 AI 改代码不出错。

---

## 快速开始

### 1. 你只需要改 6 个值

打开本文件末尾的「初始化配置」，填好你的项目信息。

### 2. 说一句话

改完后，对 AI 说：

> **"初始化项目"**

AI 会自动完成：
- 生成 `docs/项目架构宪法.md`（架构定义 + 标准形状）
- 配置数据库依赖（`requirements.txt`）
- 调整认证中间件（`middleware.py` / `main.py`）
- 输出修改清单

### 3. 开始写代码

初始化完成后，直接写业务代码。AI 已持有全套约束文件。

---

## 目录总览

```
my-project/
├── CLAUDE.md                    # AI 行为铁律（自动加载）
├── README.md                    # 本文件
├── .gitignore
│
├── docs/
│   ├── README.md                # 文档索引
│   ├── 项目架构宪法.md            # 架构定义 + 标准形状
│   └── 设计-CLAUDE内容筛选方法论.md # 审核依据
│
├── src/
│   ├── api/                     # 后端服务
│   │   ├── CLAUDE.md            # 后端框架护栏（自动关联）
│   │   ├── main.py              # 应用入口
│   │   ├── config.py            # 配置中心
│   │   ├── middleware.py        # 认证中间件
│   │   ├── models.py            # 数据模型
│   │   ├── database.py          # 数据库连接
│   │   ├── requirements.txt     # 依赖清单
│   │   └── utils/
│   │       ├── exceptions.py    # 异常体系
│   │       ├── jwt.py           # JWT 工具
│   │       └── logger.py        # 日志工具
│   └── web/                     # 前端页面
│       └── CLAUDE.md            # 前端框架护栏（自动关联）
│
├── .claude/
│   └── skills/
│       ├── think-tank/          # 智囊团
│       └── idea-evaluator/      # 立项评估

```

---

## 宪法体系

| 层级 | 文件 | 作用 | 触发时机 |
|------|------|------|---------|
| Layer 1 | `CLAUDE.md` | AI 行为铁律 + 文件关联规则 | 启动时自动加载 |
| Layer 2 | `src/api/CLAUDE.md` | 后端代码约束（架构/异常/数据库/并发） | 写后端代码前 |
| Layer 2 | `src/web/CLAUDE.md` | 前端代码约束（API/组件/存储） | 写前端代码前 |
| Layer 3 | `docs/项目架构宪法.md` | 系统架构定义 + 代码标准形状 | 首次理解项目 / 改架构时 |

---

## 预装 Skills

| Skill | 用途 | 触发 |
|-------|------|------|
| **智囊团** | 产品/技术/市场决策讨论 | `/think-tank 你的问题` |
| **立项评估** | AI 产品可行性评估 | `/idea-evaluator 你的想法` |

---

## 初始化配置

把下面的值改成你的项目，然后对 AI 说 **"初始化项目"**。

```yaml
# ===== 项目信息 =====
项目名称: 我的项目
业务描述: 一句话说清你的项目做什么

# ===== 技术栈 =====
技术栈: Python+FastAPI    # 可选: Node+Express, Go+Gin
数据库: MySQL             # 可选: PostgreSQL, SQLite, 无

# ===== 认证与部署 =====
认证方式: JWT              # 可选: OAuth, 无需认证
部署方式: Docker           # 可选: 云服务器, Serverless
```

> 改完这 6 行后，对 AI 说 "初始化项目"——AI 会自动完成所有配置。
