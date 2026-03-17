"""FastAPI 应用入口"""
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="广东省政府采购中标结果API",
    version="1.0.0",
    description="提供政府采购中标结果查询接口"
)

app.include_router(router)


@app.get("/")
def root():
    """API 根路径"""
    return {
        "message": "广东省政府采购中标结果API",
        "docs": "/docs",
        "version": "1.0.0"
    }
