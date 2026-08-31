from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import os
import glob
from app.core.mm_optimizer import run_mol_optimize_stream

router = APIRouter()


@router.websocket("/optimize")
async def optimize_websocket(websocket: WebSocket):
    # 关键：先接受连接，避免默认 Origin 检查导致 403
    await websocket.accept()
    print("WebSocket 连接已接受")

    try:
        # 接收客户端发送的参数
        data = await websocket.receive_json()
        action = data.get("action")
        if action != "optimize":
            await websocket.send_json({"type": "error", "message": "无效操作"})
            await websocket.close()
            return

        params = data.get("params", {})
        input_folder = params.get("input_folder")
        output_folder = params.get("output_folder")

        if not input_folder or not os.path.isdir(input_folder):
            await websocket.send_json({"type": "error", "message": "输入文件夹不存在"})
            await websocket.close()
            return

        if not output_folder:
            output_folder = input_folder
        os.makedirs(output_folder, exist_ok=True)

        mol_files = glob.glob(os.path.join(input_folder, "*.mol"))
        if not mol_files:
            await websocket.send_json({"type": "error", "message": "未找到 .mol 文件"})
            await websocket.close()
            return

        # 执行优化生成器，逐条发送更新
        for update in run_mol_optimize_stream(
                input_folder=input_folder,
                output_folder=output_folder,
                prefix=params.get("prefix", "opt_"),
                ff=params.get("ff", "MMFF94"),
                maxiter=int(params.get("maxiter", 500)),
                embed=params.get("embed", True),
                add_h=params.get("add_h", True),
                charge=params.get("charge", "0"),
                mult=params.get("mult", "1"),
                keyword=params.get("keyword", "#p opt b3lyp/6-31g(d,p)"),
                mem=params.get("mem", "20GB"),
                nproc=params.get("nproc", "8")
        ):
            await websocket.send_json(update)
            if update.get("type") == "done":
                break

    except WebSocketDisconnect:
        print("WebSocket 断开")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
