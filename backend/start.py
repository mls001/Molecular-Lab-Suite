import sys
import os
import uvicorn
from config import CONFIG
import app.routers.websocket
import app.routers.gjf
import app.routers.orbital


def is_frozen():
    """检测是否被 PyInstaller 打包"""
    return getattr(sys, 'frozen', False)


if __name__ == "__main__":
    backend_config = CONFIG.get("backend", {})
    host = backend_config.get("host", "127.0.0.1")
    port = backend_config.get("port", 8000)

    # 如果是打包环境，或者环境变量指定生产模式，禁用 reload
    is_production = is_frozen() or os.environ.get("MLS_PRODUCTION", "false").lower() == "true"

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=not is_production,
        log_level="info"
    )
