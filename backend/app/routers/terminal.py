from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import paramiko
import time
import threading
import asyncio

router = APIRouter()
from app.routers.remote import ssh_sessions

@router.websocket("/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    channel = None
    read_thread = None
    loop = asyncio.get_event_loop()
    closed = False

    try:
        data = await websocket.receive_json()
        session_id = data.get("session_id")
        initial_path = data.get("initial_path", "/")
        print(f"[TERMINAL] session: {session_id}, path: {initial_path}")

        if not session_id or session_id not in ssh_sessions:
            await websocket.send_json({"type": "error", "message": "Invalid session"})
            await websocket.close()
            closed = True
            return

        ssh = ssh_sessions[session_id]["ssh"]

        # 创建交互式 shell 通道
        channel = ssh.invoke_shell(term='xterm-256color', width=120, height=40)
        channel.settimeout(0.0)

        # 读取线程（持续运行）
        def reader():
            while not closed and channel and not channel.closed:
                try:
                    if channel.recv_ready():
                        data = channel.recv(4096)
                        if data:
                            try:
                                text = data.decode('utf-8', errors='replace')
                                asyncio.run_coroutine_threadsafe(
                                    websocket.send_json({"type": "output", "data": text}),
                                    loop
                                )
                            except Exception as e:
                                print(f"[TERMINAL] encode error: {e}")
                    else:
                        time.sleep(0.02)
                except Exception as e:
                    print(f"[TERMINAL] read error: {e}")
                    # 不要退出，继续循环
                    time.sleep(0.1)
            print("[TERMINAL] reader thread exited")

        read_thread = threading.Thread(target=reader, daemon=True)
        read_thread.start()

        # 发送初始回车以触发 prompt
        time.sleep(0.3)
        channel.send("\r")
        time.sleep(0.3)
        channel.send("clear\r")
        time.sleep(0.2)
        if initial_path and initial_path != '/':
            channel.send(f"cd {initial_path}\r")
            time.sleep(0.2)

        await websocket.send_json({"type": "ready"})
        print("[TERMINAL] Ready sent")

        # 主循环：接收用户输入
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
                action = msg.get("action")
                if action == "input":
                    data = msg.get("data", "")
                    if channel and not channel.closed:
                        channel.send(data)
                elif action == "resize":
                    cols = msg.get("cols", 120)
                    rows = msg.get("rows", 40)
                    if channel and not channel.closed:
                        channel.resize_pty(width=cols, height=rows)
                elif action == "close":
                    break
            except asyncio.TimeoutError:
                # 超时继续循环，保持活跃
                continue

    except WebSocketDisconnect:
        print("[TERMINAL] client disconnected (normal)")
        closed = True
    except Exception as e:
        print(f"[TERMINAL] error: {e}")
        try:
            if not closed:
                await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        closed = True
        if channel and not channel.closed:
            channel.close()
        if not closed:
            try:
                await websocket.close()
            except:
                pass