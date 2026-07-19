"""FastAPI 应用入口 — 创建 app、中间件、路由注册。"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config import Config
from middleware import JWTAuthMiddleware
from utils.exceptions import AppError

# ---- 路由 ----
from routes.analyze import router as analyze_router

app = FastAPI(
    title=Config.APP_NAME,
    version="1.0.0",
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

# ---- API 路由（必须在 StaticFiles mount 之前注册） ----
app.include_router(analyze_router)


# ===== 健康检查 =====

@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ---- 前端静态文件（最后注册，作为 fallback） ----
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


# ===== 入口 =====

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=Config.DEBUG,
    )
