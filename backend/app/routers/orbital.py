from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import os
import glob
from app.core.log_parser import parse_orbital_energies_advanced

router = APIRouter()


@router.websocket("/orbital")
async def orbital_websocket(websocket: WebSocket):
    await websocket.accept()
    print("Orbital WebSocket 连接已接受")
    try:
        data = await websocket.receive_json()
        action = data.get("action")
        if action != "parse_orbital":
            await websocket.send_json({"type": "error", "message": "无效操作"})
            await websocket.close()
            return

        folder = data.get("folder")
        if not folder or not os.path.isdir(folder):
            await websocket.send_json({"type": "error", "message": "文件夹不存在"})
            await websocket.close()
            return

        log_files = glob.glob(os.path.join(folder, "*.log"))
        if not log_files:
            await websocket.send_json({"type": "error", "message": "未找到 .log 文件"})
            await websocket.close()
            return

        total = len(log_files)
        results = []
        for idx, log_path in enumerate(log_files):
            try:
                data = parse_orbital_energies_advanced(log_path)
                results.append(data)
                await websocket.send_json({
                    "type": "progress",
                    "index": idx + 1,
                    "total": total,
                    "filename": data['filename'],
                    "status": "success"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "progress",
                    "index": idx + 1,
                    "total": total,
                    "filename": os.path.basename(log_path),
                    "status": "error",
                    "message": str(e)
                })

        # 发送所有结果
        await websocket.send_json({
            "type": "result",
            "data": results
        })

        await websocket.send_json({"type": "done", "message": f"解析完成，共处理 {total} 个文件"})

    except WebSocketDisconnect:
        print("WebSocket 断开")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
