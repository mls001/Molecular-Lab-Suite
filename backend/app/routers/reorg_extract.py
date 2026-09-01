from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import os
import glob
from app.core.reorg_parser import parse_fcclasses_output

router = APIRouter()

@router.websocket("/reorg-extract")
async def reorg_extract_websocket(websocket: WebSocket):
    await websocket.accept()
    print("Reorg Extract WebSocket 连接已接受")
    try:
        data = await websocket.receive_json()
        action = data.get("action")
        if action != "extract_reorg":
            await websocket.send_json({"type": "error", "message": "无效操作"})
            await websocket.close()
            return

        folder = data.get("folder")
        if not folder or not os.path.isdir(folder):
            await websocket.send_json({"type": "error", "message": "文件夹不存在"})
            await websocket.close()
            return

        # 查找 .out 文件
        out_files = glob.glob(os.path.join(folder, "*.out"))
        if not out_files:
            await websocket.send_json({"type": "error", "message": "未找到 .out 文件"})
            await websocket.close()
            return

        total = len(out_files)
        results = []
        for idx, file_path in enumerate(out_files):
            try:
                data = parse_fcclasses_output(file_path)
                results.append({
                    'filename': os.path.basename(file_path),
                    'frequencies': data['frequencies'],
                    'huang_rhys': data['huang_rhys'],
                    'reorg_total': data['reorg_total'],
                    'reorg_contrib': data['reorg_contrib'],
                })
                await websocket.send_json({
                    "type": "progress",
                    "index": idx + 1,
                    "total": total,
                    "filename": os.path.basename(file_path),
                    "status": "success"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "progress",
                    "index": idx + 1,
                    "total": total,
                    "filename": os.path.basename(file_path),
                    "status": "error",
                    "message": str(e)
                })

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