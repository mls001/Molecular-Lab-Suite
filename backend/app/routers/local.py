# 本地文件浏览与 FTP 传输接口（本地侧）
import os
import posixpath
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.routers.remote import ssh_sessions

router = APIRouter()


class LsRequest(BaseModel):
    path: str = "."


class PullRequest(BaseModel):
    session_id: str
    remote_path: str
    local_dir: str


class PushRequest(BaseModel):
    session_id: str
    local_path: str
    remote_dir: str


class PushDirRequest(BaseModel):
    session_id: str
    local_dir: str
    remote_dir: str


class PullDirRequest(BaseModel):
    session_id: str
    remote_dir: str
    local_dir: str


def _ensure_remote_dir(sftp, remote_path):
    norm = remote_path.replace('\\', '/')
    if not norm.startswith('/'):
        norm = '/' + norm
    current = ''
    for part in [x for x in norm.split('/') if x]:
        current = current + '/' + part if current else '/' + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            try:
                sftp.mkdir(current)
            except Exception:
                pass


@router.get("/api/local/places")
async def local_places():
    """本地常用位置（主目录/桌面/文档/下载 + 盘符），供应用内目录选择器使用"""
    home = os.path.expanduser('~')
    places = []
    for label, sub in (('主目录', ''), ('桌面', 'Desktop'), ('文档', 'Documents'), ('下载', 'Downloads')):
        path = home if not sub else os.path.join(home, sub)
        if os.path.isdir(path):
            places.append({"label": label, "path": path, "kind": "place"})
    drives = []
    if os.name == 'nt':
        import string
        for letter in string.ascii_uppercase:
            root = f"{letter}:\\"
            if os.path.exists(root):
                drives.append({"label": root, "path": root, "kind": "drive"})
    else:
        drives.append({"label": "/", "path": "/", "kind": "drive"})
    return {"home": home, "places": places, "drives": drives, "sep": os.sep}


@router.post("/api/local/ls")
async def local_ls(req: LsRequest):
    path = req.path or "."
    if not os.path.isdir(path):
        raise HTTPException(status_code=404, detail="路径不存在")
    try:
        entries = []
        for name in os.listdir(path):
            if name in ('.', '..'):
                continue
            full = os.path.join(path, name)
            try:
                is_dir = os.path.isdir(full)
                size = 0 if is_dir else os.path.getsize(full)
            except Exception:
                continue
            entries.append({"name": name, "is_dir": is_dir, "size": size})
        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"path": path, "entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/ftp/pull")
async def ftp_pull(req: PullRequest):
    """远程单个文件 → 本地目录"""
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if not os.path.isdir(req.local_dir):
        raise HTTPException(status_code=404, detail="本地目录不存在")
    sftp = ssh_sessions[req.session_id]["sftp"]
    name = os.path.basename(req.remote_path)
    local_path = os.path.join(req.local_dir, name)
    try:
        stat = sftp.stat(req.remote_path)
        size = stat.st_size
        sftp.get(req.remote_path, local_path)
        return {"name": name, "size": size, "local_path": local_path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="远程文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/ftp/push")
async def ftp_push(req: PushRequest):
    """本地单个文件 → 远程目录"""
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if not os.path.isfile(req.local_path):
        raise HTTPException(status_code=404, detail="本地文件不存在")
    sftp = ssh_sessions[req.session_id]["sftp"]
    # 本地路径是 Windows 格式，必须用 os.path.basename 取文件名
    name = os.path.basename(req.local_path)
    remote_path = posixpath.join(req.remote_dir.rstrip('/'), name)
    size = os.path.getsize(req.local_path)
    # 确保远程目录存在（含嵌套子目录）
    _ensure_remote_dir(sftp, posixpath.dirname(remote_path))
    try:
        sftp.put(req.local_path, remote_path)
        return {"name": name, "size": size, "remote_path": remote_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/ftp/push-dir")
async def ftp_push_dir(req: PushDirRequest):
    """本地文件夹(递归) → 远程"""
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if not os.path.isdir(req.local_dir):
        raise HTTPException(status_code=404, detail="本地目录不存在")
    sftp = ssh_sessions[req.session_id]["sftp"]
    base = req.remote_dir.rstrip('/')
    # 先确保远程目标目录（含中间目录）已创建
    _ensure_remote_dir(sftp, base)
    count = 0
    total_size = 0
    try:
        for root, dirs, files in os.walk(req.local_dir):
            rel = os.path.relpath(root, req.local_dir)
            rel_posix = rel.replace('\\', '/')
            parent_remote = posixpath.join(base, rel_posix) if rel != '.' else base
            if rel != '.':
                _ensure_remote_dir(sftp, parent_remote)
            for fn in files:
                lp = os.path.join(root, fn)
                rp = posixpath.join(parent_remote, fn)
                sftp.put(lp, rp)
                try:
                    total_size += os.path.getsize(lp)
                except Exception:
                    pass
                count += 1
        return {"count": count, "size": total_size}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/ftp/pull-dir")
async def ftp_pull_dir(req: PullDirRequest):
    """远程文件夹(递归) → 本地"""
    if req.session_id not in ssh_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if not os.path.isdir(req.local_dir):
        raise HTTPException(status_code=404, detail="本地目录不存在")
    sftp = ssh_sessions[req.session_id]["sftp"]
    count = 0
    total_size = 0

    def walk(remote_dir, local_dir):
        nonlocal count, total_size
        try:
            attrs = sftp.listdir_attr(remote_dir)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"远程目录不存在: {remote_dir}")
        for a in attrs:
            if a.filename in ('.', '..'):
                continue
            rp = posixpath.join(remote_dir, a.filename)
            lp = os.path.join(local_dir, a.filename)
            is_dir = (a.st_mode & 0o040000) != 0
            if is_dir:
                os.makedirs(lp, exist_ok=True)
                walk(rp, lp)
            else:
                sftp.get(rp, lp)
                count += 1
                total_size += a.st_size

    try:
        base_local = os.path.join(req.local_dir, os.path.basename(req.remote_dir.rstrip('/')) or 'remote')
        os.makedirs(base_local, exist_ok=True)
        walk(req.remote_dir, base_local)
        return {"count": count, "size": total_size, "local_dir": base_local}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
