from fastapi import WebSocket, WebSocketDisconnect
import json
import uuid
from app.core.mm_optimizer import run_mol_optimize_stream


async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "optimize":
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

                # 执行优化生成器
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

    except WebSocketDisconnect:
        print("WebSocket 连接断开")
