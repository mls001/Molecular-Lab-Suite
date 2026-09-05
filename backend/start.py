import sys
import os

# 中文 Windows 控制台默认 GBK 编码，打印 ✅🚀 等 emoji 会抛 UnicodeEncodeError 导致启动崩溃。
# 这里统一把标准输出/错误重配为 UTF-8（打包进无 Python 电脑后同样适用）。
for _stream_name in ("stdout", "stderr"):
    _s = getattr(sys, _stream_name, None)
    if _s is not None:
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import uvicorn
from config import CONFIG
import app.routers.websocket
import app.routers.gjf
import app.routers.orbital
import app.routers.td
import app.routers.reorg
import app.routers.reorg_extract
import app.routers.remote
import app.routers.preset
import app.routers.terminal
import app.routers.local
import app.routers.soc
import cryptography
import cryptography.fernet
import cryptography.hazmat
import cryptography.hazmat.primitives
import cryptography.hazmat.primitives.kdf.pbkdf2


def is_frozen():
    """检测是否被 PyInstaller 打包（现在永远返回 False）"""
    return False


if __name__ == "__main__":
    backend_config = CONFIG.get("backend", {})
    host = backend_config.get("host", "127.0.0.1")
    port = backend_config.get("port", 8002)  # fallback 改为 8002

    # 生产环境（通过 Electron 启动）禁用 reload
    is_production = os.environ.get("MLS_PRODUCTION", "false").lower() == "true"

    print(f"🚀 启动后端服务: {host}:{port}")
    print(f"📁 生产模式: {is_production}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=not is_production,
        log_level="info"
    )