-- ============================================================
-- Sourcely V1 — 数据库 Schema
-- 引擎: MySQL 8.0 / InnoDB / utf8mb4
-- 日期: 2026-07-21
-- ============================================================

CREATE DATABASE IF NOT EXISTS sourcely_DB
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE sourcely_DB;

-- ============================================================
-- 1. users — Google 登录用户
-- ============================================================
CREATE TABLE users (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  google_id   VARCHAR(100) NOT NULL UNIQUE COMMENT 'Google sub claim',
  email       VARCHAR(200) COMMENT 'Google 账号邮箱，可空',
  name        VARCHAR(200) COMMENT 'Google 账号显示名',
  avatar_url  VARCHAR(500) COMMENT 'Google 头像 URL',
  created_at  DATETIME DEFAULT NOW(),
  last_login  DATETIME DEFAULT NOW() COMMENT '每次登录更新'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Google 登录用户';

-- ============================================================
-- 2. analysis — 分析记录（主表）
-- ============================================================
CREATE TABLE analysis (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  user_id         INT NOT NULL,
  offer_id        VARCHAR(30) NOT NULL COMMENT '1688 offerId',
  status          ENUM('pending','running','done','failed') DEFAULT 'pending' COMMENT '分析状态',

  -- 商品基础信息（元数据，不存完整 JSON）
  title           VARCHAR(500) COMMENT '商品标题',
  price_min       DECIMAL(10,2) COMMENT '最低单价',
  price_max       DECIMAL(10,2) COMMENT '最高单价',
  moq             INT COMMENT '最小起订量',
  unit            VARCHAR(10) COMMENT '单位（把/件/个）',

  -- 店铺信息
  shop_name       VARCHAR(200) COMMENT '店铺名称',
  shop_years      INT COMMENT '开店年限',
  shop_rate       DECIMAL(3,1) COMMENT '好评率 %',
  repurchase      DECIMAL(4,1) COMMENT '回头率 %',
  sold            INT COMMENT '累计销量',

  -- 判词（V1 规则引擎输出）
  verdict_product VARCHAR(200) COMMENT '产品判词',
  verdict_factory VARCHAR(200) COMMENT '工厂判词',
  verdict_sample  VARCHAR(200) COMMENT '拿样判词',

  -- 追踪
  apify_task_id   VARCHAR(50) COMMENT 'Apify 任务 ID',
  created_at      DATETIME DEFAULT NOW(),
  updated_at      DATETIME DEFAULT NOW() ON UPDATE NOW(),

  UNIQUE KEY uk_offer_user (offer_id, user_id) COMMENT '同一用户不重复分析同一商品',
  KEY idx_user (user_id),
  KEY idx_status (status),
  KEY idx_created (created_at),
  FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='商品分析记录';

-- ============================================================
-- 3. analysis_spec — 规格参数（1:N）
-- ============================================================
CREATE TABLE analysis_spec (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  analysis_id INT NOT NULL,
  spec_key    VARCHAR(100) COMMENT '规格名（工艺/材质/尺寸/风格）',
  spec_value  VARCHAR(200) COMMENT '规格值',
  FOREIGN KEY (analysis_id) REFERENCES analysis(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='商品规格参数';

-- ============================================================
-- 4. analysis_sku — SKU 变体（1:N）
-- ============================================================
CREATE TABLE analysis_sku (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  analysis_id INT NOT NULL,
  sku_name    VARCHAR(200) COMMENT 'SKU 名称（颜色/款式）',
  sku_image   VARCHAR(500) COMMENT 'SKU 缩略图 URL',
  FOREIGN KEY (analysis_id) REFERENCES analysis(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='SKU 变体';

-- ============================================================
-- 5. analysis_price_tier — 阶梯价格（1:N）
-- ============================================================
CREATE TABLE analysis_price_tier (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  analysis_id INT NOT NULL,
  qty_min     INT COMMENT '数量下限',
  qty_max     INT COMMENT '数量上限（可空=以上）',
  unit_price  DECIMAL(10,2) COMMENT '单价',
  FOREIGN KEY (analysis_id) REFERENCES analysis(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='阶梯批发价';

-- ============================================================
-- V1.1 迁移：历史记录需要商品缩略图
-- ============================================================
ALTER TABLE analysis ADD COLUMN image_url VARCHAR(500) COMMENT '商品主图URL' AFTER title;
