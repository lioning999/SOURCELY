#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OfferCopilot 职通车AI — API 入口
启动: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from database import AsyncDatabaseConnection
from config import Config

# ── 配置 ────────────────────────────────────────────
config = Config()
config.validate()

# ── FastAPI 应用 ────────────────────────────────────
app = FastAPI(
    title="OfferCopilot 职通车AI",
    description="AI简历智能诊断与优化服务",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── JWT 认证中间件（内层）────────────────────────────
from middleware import jwt_auth_middleware
app.middleware("http")(jwt_auth_middleware)

# ── CORS（最外层，必须在 JWT 之后注册以保证执行链正确）──
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# ── 数据库连接池生命周期 ─────────────────────────────

@app.on_event("startup")
async def startup():
    await AsyncDatabaseConnection.get_pool()
    conn = await AsyncDatabaseConnection.get_connection()
    try:
        await conn.ping(reconnect=True)
    finally:
        await AsyncDatabaseConnection.close_connection(conn)

@app.on_event("shutdown")
async def shutdown():
    await AsyncDatabaseConnection.close_pool()

# ── 健康检查 ────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "running", "service": "OfferCopilot", "version": "2.0.0"}

@app.get("/health")
async def health():
    try:
        conn = await AsyncDatabaseConnection.get_connection()
        try:
            await conn.ping(reconnect=False)
        finally:
            await AsyncDatabaseConnection.close_connection(conn)
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy"})

# ── 路由注册 ────────────────────────────────────────
from routes.auth import router as auth_router
app.include_router(auth_router, tags=["认证"])
from routes.resume_upload import router as resume_upload_router
app.include_router(resume_upload_router, tags=["简历"])
from routes.resume_diagnose import router as resume_diagnose_router
app.include_router(resume_diagnose_router, tags=["简历"])
from routes.resume_optimize import router as resume_optimize_router
app.include_router(resume_optimize_router, tags=["简历"])
from routes.pay import router as pay_router
app.include_router(pay_router, tags=["支付"])

# ── 全局异常处理 ────────────────────────────────────
from utils.exceptions import AppError

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "服务器内部错误",
            "detail": str(exc) if config.TEST_MODE else None,
        },
    )

# ── 调试端点（仅测试模式）────────────────────────────
if config.TEST_MODE:
    # 敏感键名精确匹配，避免误杀模型参数（如 AI_MAX_TOKENS）
    _SENSITIVE_KEYS = {
        "DASHSCOPE_API_KEY", "JWT_SECRET_KEY",
        "DATABASE_PASSWORD", "WECHAT_SECRET", "WXPAY_APIV3_KEY",
        "WXPAY_PRIVATE_KEY_PATH", "WXPAY_PUBLIC_KEY_PATH",
        "WXPAY_CERT_SERIAL_NO",
    }

    @app.get("/debug/config")
    async def debug_config():
        safe = {}
        for k, v in vars(Config).items():
            if k.startswith("_") or k in _SENSITIVE_KEYS:
                continue
            safe[k] = v
        return safe

    @app.post("/debug/mock-payment/{out_trade_no}")
    async def debug_mock_payment(out_trade_no: str):
        """模拟支付成功 — 仅测试模式。标记订单 paid + 标记诊断已付。"""
        from repositories.orders import OrderRepository
        from repositories.diagnoses import DiagnosisRepository

        txn_id = f"TXN_MOCK_{out_trade_no[:8]}"
        paid = await OrderRepository.mark_paid(out_trade_no, txn_id)
        if paid is None:
            return {"ok": False, "message": "订单不存在或已支付"}
        diagnosis_id = paid.get("diagnosis_id")
        if diagnosis_id:
            await DiagnosisRepository.mark_paid(diagnosis_id, paid["openid"])
        return {"ok": True, "message": f"已模拟支付: {out_trade_no}"}

# ── 前端静态文件（所有 API 路由注册之后）─────────────
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.SERVER_HOST, port=config.SERVER_PORT,
                reload=config.TEST_MODE, log_level=config.LOG_LEVEL.lower())
