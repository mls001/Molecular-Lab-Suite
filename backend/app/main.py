from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from app.routers import websocket

app = FastAPI(title="分子工具 API", version="1.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 路由
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "optimize":
                from app.core.mm_optimizer import run_mol_optimize_stream
                params = data.get("params", {})
                input_folder = params.get("input_folder")
                output_folder = params.get("output_folder")
                prefix = params.get("prefix", "opt_")
                ff = params.get("ff", "MMFF94")
                maxiter = int(params.get("maxiter", 500))
                embed = params.get("embed", True)
                add_h = params.get("add_h", True)
                charge = params.get("charge", "0")
                mult = params.get("mult", "1")
                keyword = params.get("keyword", "#p opt b3lyp/6-31g(d,p)")
                mem = params.get("mem", "20GB")
                nproc = params.get("nproc", "8")

                for update in run_mol_optimize_stream(
                    input_folder, output_folder, prefix, ff,
                    maxiter, embed, add_h, charge, mult,
                    keyword, mem, nproc
                ):
                    await websocket.send_json(update)
                    if update.get("type") == "done":
                        break
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
    except Exception as e:
        print(f"WebSocket 错误: {e}")


@app.get("/")
async def root():
    return {"message": "分子工具 API 运行中", "version": "1.0"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)