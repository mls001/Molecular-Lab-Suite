from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import paramiko
import uuid
import posixpath
import os

router = APIRouter()

# 全局存储 SSH 会话
ssh_sessions = {}

class ConnectRequest(BaseModel):
    host: str
    port: int = 22
    username: str
    password: str = ""
    auth_method: str = "password"
    key_file: str = ""

class LsRequest(BaseModel):
    session_id: str
    path: str

@router.post("/api/remote/connect")
async def connect_ssh(req: ConnectRequest):
    # ... 清理旧会话 ...

    session_id = str(uuid.uuid4())
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if req.auth_method == "password":
            client.connect(
                hostname=req.host,
                port=req.port,
                username=req.username,
                password=req.password,
                timeout=10
            )
        else:
            key = paramiko.RSAKey.from_private_key_file(os.path.expanduser(req.key_file))
            client.connect(
                hostname=req.host,
                port=req.port,
                username=req.username,
                pkey=key,
                timeout=10
            )
        ssh_sessions[session_id] = {
            "ssh": client,
            "sftp": client.open_sftp(),
            "host": req.host,
            "port": req.port,
            "username": req.username,
            "password": req.password  # 存储密码用于任务连接
        }
        print(f"[REMOTE] Session created: {session_id}, total: {len(ssh_sessions)}")
        return {"session_id": session_id, "message": "连接成功"}
    except Exception as e:
        if session_id in ssh_sessions:
            try:
                ssh_sessions[session_id]["sftp"].close()
                ssh_sessions[session_id]["ssh"].close()
            except:
                pass
            del ssh_sessions[session_id]
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/remote/ls")
async def list_remote(req: LsRequest):
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    sftp = ssh_sessions[req.session_id]["sftp"]
    try:
        items = sftp.listdir_attr(req.path)
        entries = []
        for attr in items:
            name = attr.filename
            if name in ('.', '..'):
                continue
            is_dir = (attr.st_mode & 0o040000) != 0
            is_link = (attr.st_mode & 0o0120000) == 0o0120000
            if is_link:
                try:
                    target = sftp.stat(posixpath.join(req.path, name))
                    is_dir = (target.st_mode & 0o040000) != 0
                except:
                    pass
            entries.append({
                "name": name,
                "is_dir": is_dir,
                "size": attr.st_size
            })
        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"entries": entries, "current_path": req.path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="路径不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/remote/disconnect")
async def disconnect_ssh(session_id: str):
    if session_id in ssh_sessions:
        try:
            ssh_sessions[session_id]["sftp"].close()
            ssh_sessions[session_id]["ssh"].close()
        except:
            pass
        del ssh_sessions[session_id]
        print(f"[REMOTE] Disconnected: {session_id}, remaining: {len(ssh_sessions)}")
        return {"message": "已断开连接"}
    raise HTTPException(status_code=404, detail="会话不存在")

__all__ = ['ssh_sessions']