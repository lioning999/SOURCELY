"""FastAPI 应用入口 — 创建 app、中间件、路由注册。"""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import Config
from database import AsyncDatabaseConnection
from middleware import JWTAuthMiddleware
from routes.auth import auth_router, callback_router
from routes.analyze import router as analyze_router
from routes.history import router as history_router
from utils.exceptions import AppError


# ---- 生命周期 ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动：初始化数据库连接池。关闭：释放连接池。"""
    await AsyncDatabaseConnection.get_pool()
    yield
    await AsyncDatabaseConnection.close_pool()


app = FastAPI(
    title=Config.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if Config.TEST_MODE else None,
    redoc_url=None,
)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 生产环境限定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- JWT 认证中间件 ----
app.add_middleware(JWTAuthMiddleware)

# ---- 全局异常处理器 ----
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "data": None, "message": "输入验证失败"},
    )


# ===== 健康检查 =====
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ---- API 路由（必须在 StaticFiles mount 之前注册） ----
app.include_router(auth_router)
app.include_router(callback_router)
app.include_router(analyze_router)
app.include_router(history_router)


# ---- 前端静态文件（最后注册，作为 fallback） ----
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


# ===== 入口 =====
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=Config.PORT,
        reload=Config.DEBUG,
    )
