from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import os
import paramiko
import threading
from app.routers.remote import ssh_sessions  # 导入 remote 模块的会话字典

router = APIRouter()


@router.websocket("/reorg")
async def reorg_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        action = data.get("action")
        if action != "run_reorg":
            await websocket.send_json({"type": "error", "message": "无效操作"})
            await websocket.close()
            return

        params = data.get("params", {})
        session_id = params.get("session_id")
        workdir = params.get("workdir")
        file_arg = params.get("file_arg")
        g = params.get("g", "b3lyp")
        o = params.get("o", "b3lyp/G")
        gb = params.get("gb", "6-31G(d,p)")
        ob = params.get("ob", "")
        root = params.get("root", "1")
        sm = params.get("sm", "1")
        c = params.get("c", "0")
        state1 = params.get("state1")
        state2 = params.get("state2")
        ic = params.get("ic", "off")

        if not workdir or not file_arg:
            await websocket.send_json({"type": "error", "message": "缺少工作目录或文件参数"})
            await websocket.close()
            return

        # 从会话字典中获取 SSH 客户端
        ssh_client = None
        if session_id and session_id in ssh_sessions:
            ssh_client = ssh_sessions[session_id]["ssh"]
            await websocket.send_json({"type": "info", "message": "使用已有 SSH 会话"})
        else:
            # 若会话不存在，返回明确错误
            await websocket.send_json({"type": "error", "message": "SSH 会话已过期或无效，请重新连接"})
            await websocket.close()
            return

        # 构建命令
        cmd_parts = [
            f"g='{g}'",
            f"o='{o}'",
            f"gb='{gb}'",
            f"ob='{ob}'" if ob else "",
            f"root={root}",
            f"sm={sm}",
            f"c={c}"
        ]
        cmd_parts = [p for p in cmd_parts if p]
        if state1:
            cmd_parts.append(f"state1={state1}")
        if state2:
            cmd_parts.append(f"state2={state2}")
        if ic == "off":
            cmd_parts.append("ic=off")

        cmd = f"nomap.sh {file_arg} " + " ".join(cmd_parts)
        full_cmd = f"cd {workdir} && {cmd}"

        await websocket.send_json({"type": "info", "message": f"📝 执行命令: {full_cmd}"})

        # 执行命令
        stdin, stdout, stderr = ssh_client.exec_command(full_cmd)

        def read_stream(stream, tag):
            for line in iter(stream.readline, ''):
                if line.strip():
                    websocket.send_json({"type": "log", "tag": tag, "message": line.rstrip()})

        t1 = threading.Thread(target=read_stream, args=(stdout, "STDOUT"))
        t2 = threading.Thread(target=read_stream, args=(stderr, "STDERR"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        exit_status = stdout.channel.recv_exit_status()
        await websocket.send_json({"type": "done", "message": f"任务完成，退出码: {exit_status}"})

    except WebSocketDisconnect:
        print("WebSocket 断开")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
