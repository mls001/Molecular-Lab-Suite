from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import paramiko
import uuid
import posixpath
import os
import tempfile
import shutil

router = APIRouter()

# 全局存储 SSH 会话
ssh_sessions = {}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_ROOT = os.path.join(PROJECT_ROOT, "cache")


def get_cache_dir(session_id: str) -> str:
    cache_dir = os.path.join(CACHE_ROOT, session_id)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def clear_cache(session_id: str):
    cache_dir = get_cache_dir(session_id)
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir, ignore_errors=True)


# ========== 请求模型 ==========
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


class FileReadRequest(BaseModel):
    session_id: str
    path: str


class FileSaveRequest(BaseModel):
    session_id: str
    path: str
    content: str


class FileRenameRequest(BaseModel):
    session_id: str
    old_path: str
    new_path: str


class BatchDownloadRequest(BaseModel):
    session_id: str
    paths: list[str]


class BatchUploadRequest(BaseModel):
    session_id: str
    files: list[dict]  # [{"remote_path": "...", "cache_path": "..."}]


# ========== 连接管理 ==========
@router.post("/connect")
async def connect_ssh(req: ConnectRequest):
    to_delete = []
    for sid, session in ssh_sessions.items():
        if (session.get("host") == req.host and
                session.get("port") == req.port and
                session.get("username") == req.username):
            try:
                session["sftp"].close()
                session["ssh"].close()
            except:
                pass
            to_delete.append(sid)
    for sid in to_delete:
        del ssh_sessions[sid]

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
            "password": req.password
        }
        print(f"[REMOTE] Session created: {session_id}")
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


@router.delete("/disconnect")
async def disconnect_ssh(session_id: str):
    if session_id in ssh_sessions:
        try:
            ssh_sessions[session_id]["sftp"].close()
            ssh_sessions[session_id]["ssh"].close()
        except:
            pass
        # 清理缓存
        clear_cache(session_id)
        del ssh_sessions[session_id]
        print(f"[REMOTE] Disconnected: {session_id}")
        return {"message": "已断开连接"}
    raise HTTPException(status_code=404, detail="会话不存在")


# ========== 目录列表 ==========
@router.post("/ls")
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


# ========== 文件下载（远程→缓存） ==========
@router.post("/download")
async def remote_download_file(req: FileReadRequest):
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    sftp = ssh_sessions[req.session_id]["sftp"]
    cache_dir = get_cache_dir(req.session_id)
    cache_filename = os.path.basename(req.path)
    cache_path = os.path.join(cache_dir, cache_filename)
    try:
        sftp.get(req.path, cache_path)
        with open(cache_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content, "cache_path": cache_path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="远程文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 文件上传（缓存→远程） ==========
@router.post("/upload")
async def remote_upload_file(req: FileSaveRequest):
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    sftp = ssh_sessions[req.session_id]["sftp"]
    cache_dir = get_cache_dir(req.session_id)
    cache_filename = os.path.basename(req.path)
    cache_path = os.path.join(cache_dir, cache_filename)

    # 🔥 关键：无论缓存是否存在，都用传入的 content 覆盖缓存
    if req.content is not None:
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(req.content)
    elif not os.path.exists(cache_path):
        raise HTTPException(status_code=404, detail="缓存文件不存在且未提供内容")

    try:
        # 确保远程目录存在（原代码）
        dirname = posixpath.dirname(req.path)
        if dirname:
            parts = dirname.split('/')
            current = ''
            for part in parts:
                if not part:
                    continue
                current = posixpath.join(current, part) if current else part
                try:
                    sftp.stat(current)
                except FileNotFoundError:
                    sftp.mkdir(current)
        sftp.put(cache_path, req.path)
        # ❌ 绝对不要删除缓存！注释掉下面这行
        # os.remove(cache_path)
        return {"message": "上传成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 批量下载 ==========
@router.post("/batch-download")
async def remote_batch_download(req: BatchDownloadRequest):
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    sftp = ssh_sessions[req.session_id]["sftp"]
    cache_dir = get_cache_dir(req.session_id)
    results = []
    for remote_path in req.paths:
        cache_filename = os.path.basename(remote_path)
        cache_path = os.path.join(cache_dir, cache_filename)
        try:
            sftp.get(remote_path, cache_path)
            results.append({"path": remote_path, "cache_path": cache_path, "status": "success"})
        except Exception as e:
            results.append({"path": remote_path, "status": "error", "message": str(e)})
    return {"results": results}


# ========== 批量上传 ==========
@router.post("/batch-upload")
async def remote_batch_upload(req: BatchUploadRequest):
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    sftp = ssh_sessions[req.session_id]["sftp"]
    cache_dir = get_cache_dir(req.session_id)  # 获取该会话的缓存根目录
    results = []
    for item in req.files:
        remote_path = item.get("remote_path")
        cache_filename = item.get("cache_path")  # 前端只传文件名
        if not remote_path or not cache_filename:
            results.append({"remote_path": remote_path, "status": "error", "message": "参数缺失"})
            continue
        cache_full_path = os.path.join(cache_dir, cache_filename)  # 拼接完整路径
        if not os.path.exists(cache_full_path):
            results.append({"remote_path": remote_path, "status": "error", "message": "缓存文件不存在"})
            continue
        try:
            # 确保远程目录存在（原有代码已实现）
            dirname = posixpath.dirname(remote_path)
            if dirname:
                try:
                    sftp.stat(dirname)
                except FileNotFoundError:
                    parts = dirname.split('/')
                    current = ''
                    for part in parts:
                        if not part:
                            continue
                        current = posixpath.join(current, part) if current else part
                        try:
                            sftp.stat(current)
                        except FileNotFoundError:
                            sftp.mkdir(current)
            sftp.put(cache_full_path, remote_path)
            os.remove(cache_full_path)  # 上传后删除缓存，释放空间
            results.append({"remote_path": remote_path, "status": "success"})
        except Exception as e:
            results.append({"remote_path": remote_path, "status": "error", "message": str(e)})
    return {"results": results}


# ========== 清理缓存 ==========
@router.delete("/cache")
async def clear_remote_cache(session_id: str):
    if session_id in ssh_sessions:
        clear_cache(session_id)
        return {"message": "缓存已清理"}
    raise HTTPException(status_code=404, detail="会话不存在")


# ========== 从缓存读取文件内容（用于编辑器） ==========
@router.post("/cache/read")
async def read_cache_file(req: FileReadRequest):
    # 不需要session验证，因为缓存是本地的
    cache_dir = get_cache_dir(req.session_id)
    cache_filename = os.path.basename(req.path)
    cache_path = os.path.join(cache_dir, cache_filename)
    if not os.path.exists(cache_path):
        raise HTTPException(status_code=404, detail="缓存文件不存在")
    with open(cache_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return {"content": content}


# ========== 写入缓存文件 ==========
@router.post("/cache/write")
async def write_cache_file(req: FileSaveRequest):
    cache_dir = get_cache_dir(req.session_id)
    cache_filename = os.path.basename(req.path)
    cache_path = os.path.join(cache_dir, cache_filename)
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(req.content)
        return {"message": "缓存写入成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 导出 ssh_sessions ==========
__all__ = ['ssh_sessions']
