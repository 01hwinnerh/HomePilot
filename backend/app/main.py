from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.app_debug,
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """用于 Docker、监控和本地开发的无依赖存活探针。"""

    return {"status": "ok", "environment": settings.app_env}
