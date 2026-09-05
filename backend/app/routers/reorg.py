from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import os
import paramiko
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()
from app.routers.remote import ssh_sessions

# 线程池用于执行 SSH 命令
executor = ThreadPoolExecutor(max_workers=5)

@router.websocket("/reorg")
async def reorg_websocket(websocket: WebSocket):
    await websocket.accept()
    task_ssh_client = None
    loop = asyncio.get_event_loop()
    message_queue = asyncio.Queue()

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
        coord = params.get("coord", "CARTESIAN")
        state1 = params.get("state1")
        state2 = params.get("state2")
        ic = params.get("ic", "off")

        if not workdir or not file_arg:
            await websocket.send_json({"type": "error", "message": "缺少工作目录或文件参数"})
            await websocket.close()
            return

        if not session_id or session_id not in ssh_sessions:
            await websocket.send_json({"type": "error", "message": "无效的会话，请通过工具栏连接服务器"})
            await websocket.close()
            return

        main_session = ssh_sessions[session_id]
        host = main_session.get("host")
        port = main_session.get("port")
        username = main_session.get("username")
        password = main_session.get("password")

        if not host or not username:
            await websocket.send_json({"type": "error", "message": "会话缺少连接信息，请重新连接"})
            await websocket.close()
            return

        # 在独立线程中建立 SSH 连接并执行命令
        def run_task():
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=15
                )
                cmd_parts = [
                    f"g='{g}'",
                    f"o='{o}'",
                    f"gb='{gb}'",
                    f"ob='{ob}'" if ob else "",
                    f"root={root}",
                    f"sm={sm}",
                    f"c={c}",
                    f"coord={coord}"
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

                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "info", "message": f"执行命令: {full_cmd}"}),
                    loop
                )

                stdin, stdout, stderr = client.exec_command(full_cmd)

                # 读取输出并放入队列
                def read_stream(stream, tag):
                    for line in iter(stream.readline, ''):
                        if line.strip():
                            asyncio.run_coroutine_threadsafe(
                                message_queue.put({"type": "log", "tag": tag, "message": line.rstrip()}),
                                loop
                            )

                t1 = threading.Thread(target=read_stream, args=(stdout, "STDOUT"))
                t2 = threading.Thread(target=read_stream, args=(stderr, "STDERR"))
                t1.start()
                t2.start()
                t1.join()
                t2.join()

                exit_status = stdout.channel.recv_exit_status()
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "done", "message": f"任务完成，退出码: {exit_status}"}),
                    loop
                )
                client.close()
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "error", "message": str(e)}),
                    loop
                )

        # 启动后台任务
        future = loop.run_in_executor(executor, run_task)

        # 主循环：处理 WebSocket 消息（用户输入）和队列消息
        while True:
            # 同时监听 websocket 消息和队列消息
            recv_task = asyncio.create_task(websocket.receive_json())
            queue_task = asyncio.create_task(message_queue.get())

            done, pending = await asyncio.wait(
                [recv_task, queue_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # 处理队列消息
            if queue_task in done:
                msg = queue_task.result()
                await websocket.send_json(msg)

            # 处理 WebSocket 消息
            if recv_task in done:
                msg = recv_task.result()
                action = msg.get("action")
                if action == "input":
                    # 任务不需要交互输入，忽略
                    pass
                elif action == "close":
                    break

            # 取消未完成的任务
            for task in pending:
                task.cancel()

    except WebSocketDisconnect:
        print("WebSocket 断开")
    except Exception as e:
        print(f"错误: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        await websocket.close()