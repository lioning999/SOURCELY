-- db/schema.sql — OfferCopilot MVP 数据库 DDL（4 张表）
-- 新部署直接执行本文件。引擎: InnoDB, 字符集: utf8mb4

-- ── members 用户表 ────────────────────────────────

CREATE TABLE IF NOT EXISTS members (
    openid          VARCHAR(100) NOT NULL COMMENT '微信 openid',
    nickname        VARCHAR(100) DEFAULT NULL COMMENT '微信昵称',
    avatar_url      VARCHAR(500) DEFAULT NULL COMMENT '微信头像',
    optimize_remain INT          DEFAULT 0  COMMENT '剩余优化次数',
    preview_remain  INT          DEFAULT 2  COMMENT '剩余预览次数',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (openid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── resumes 简历表 ───────────────────────────────────

CREATE TABLE IF NOT EXISTS resumes (
    id          VARCHAR(36)  NOT NULL COMMENT 'UUID',
    openid      VARCHAR(100) NOT NULL COMMENT '上传用户 openid',
    filename    VARCHAR(255) DEFAULT NULL COMMENT '原始文件名',
    raw_text    TEXT         NOT NULL COMMENT '提取的简历文本',
    file_size   INT          DEFAULT 0 COMMENT '文件大小(字节)',
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_resumes_openid (openid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── diagnoses 诊断+优化结果表 ──────────────────────────

CREATE TABLE IF NOT EXISTS diagnoses (
    id              VARCHAR(36)  NOT NULL COMMENT 'UUID',
    resume_id       VARCHAR(36)  NOT NULL COMMENT '关联 resumes.id',
    openid          VARCHAR(100) NOT NULL COMMENT '用户 openid',
    diagnose_result JSON         DEFAULT NULL COMMENT 'AI 诊断完整输出',
    optimized_text      TEXT DEFAULT NULL COMMENT '优化后简历全文',
    before_after_pairs  JSON DEFAULT NULL COMMENT '优化前后对比对',
    interview_qa        JSON DEFAULT NULL COMMENT '追问预判',
    interview_questions JSON DEFAULT NULL COMMENT '模拟面试题',
    is_paid         TINYINT      DEFAULT 0  COMMENT '0=未付 1=已付',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    optimized_at    TIMESTAMP    NULL DEFAULT NULL COMMENT '最后一次优化时间',
    PRIMARY KEY (id),
    INDEX idx_diag_resume (resume_id),
    INDEX idx_diag_openid (openid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── orders 支付订单表 ──────────────────────────────────

CREATE TABLE IF NOT EXISTS orders (
    id              VARCHAR(36)  NOT NULL COMMENT 'UUID',
    openid          VARCHAR(100) NOT NULL COMMENT '用户 openid',
    resume_id       VARCHAR(36)  DEFAULT NULL COMMENT '关联 resumes.id（优化时关联，购买时不关联）',
    out_trade_no    VARCHAR(32)  NOT NULL COMMENT '微信商户订单号',
    transaction_id  VARCHAR(64)  DEFAULT NULL COMMENT '微信支付交易号',
    plan            TINYINT      NOT NULL DEFAULT 1 COMMENT '套餐 1=体验装 2=进阶装',
    times           INT          NOT NULL DEFAULT 1 COMMENT '套餐包含优化次数',
    status          VARCHAR(20)  DEFAULT 'pending' COMMENT 'pending | paid',
    amount          INT          NOT NULL COMMENT '金额(分)',
    diagnosis_id    VARCHAR(36)  DEFAULT NULL COMMENT '关联 diagnoses.id（按次付费）',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    paid_at         TIMESTAMP    NULL DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_out_trade_no (out_trade_no),
    INDEX idx_orders_openid (openid),
    INDEX idx_orders_resume (resume_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 迁移：v2.2→v2.3 优化对比对 ──────────────────────
-- ALTER TABLE diagnoses ADD COLUMN before_after_pairs JSON DEFAULT NULL COMMENT '优化前后对比对';
-- ── 迁移：v2.1→v2.2 预览次数 ──────────────────────
-- ALTER TABLE members ADD COLUMN preview_remain INT DEFAULT 2 COMMENT '剩余预览次数';
-- ── 迁移：v3.0 按次付费 ──────────────────────────────
-- ALTER TABLE diagnoses ADD COLUMN is_paid TINYINT DEFAULT 0 COMMENT '0=未付 1=已付' AFTER interview_questions;
-- ALTER TABLE orders ADD COLUMN diagnosis_id VARCHAR(36) DEFAULT NULL COMMENT '关联 diagnoses.id（按次付费）' AFTER amount;
-- ── 迁移：v2.0→v2.1 支付两档改造 ───────────────────────
-- 已有数据库执行以下 ALTER（新部署直接 CREATE TABLE 即可）
-- ALTER TABLE members ADD COLUMN optimize_remain INT DEFAULT 0 COMMENT '剩余优化次数' AFTER avatar_url;
-- ALTER TABLE orders ADD COLUMN plan TINYINT NOT NULL DEFAULT 1 COMMENT '套餐 1=体验装 2=进阶装' AFTER amount;
-- ALTER TABLE orders ADD COLUMN times INT NOT NULL DEFAULT 1 COMMENT '套餐包含优化次数' AFTER plan;
-- ALTER TABLE orders MODIFY COLUMN resume_id VARCHAR(36) NULL COMMENT '关联 resumes.id';
