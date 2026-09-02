from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import glob
import tempfile
from urllib.parse import unquote
from app.core.gjf_modifier import modify_gjf_content
from typing import List
router = APIRouter()


# ========== HTTP 端点 ==========

@router.get("/list")
async def list_files(path: str):
    path = unquote(path).replace('/', os.sep).replace('\\', os.sep)
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="无效目录")
    files = [os.path.basename(f) for f in glob.glob(os.path.join(path, "*.gjf"))]
    files += [os.path.basename(f) for f in glob.glob(os.path.join(path, "*.GJF"))]
    files = sorted(set(files))
    return {"files": files}


class FileReadRequest(BaseModel):
    path: str


@router.post("/read")
async def read_file(req: FileReadRequest):
    if not os.path.exists(req.path):
        raise HTTPException(status_code=404, detail="文件不存在")
    try:
        with open(req.path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FileSaveRequest(BaseModel):
    path: str
    content: str


@router.post("/save")
async def save_file(req: FileSaveRequest):
    try:
        os.makedirs(os.path.dirname(req.path), exist_ok=True)
        with open(req.path, 'w', encoding='utf-8') as f:
            f.write(req.content)
        return {"message": "保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ApplyParamsRequest(BaseModel):
    content: str
    mem: str
    nproc: str
    keyword: str
    charge: str
    mult: str
    chk_name: str = None   # 新增可选字段

@router.post("/apply-params")
async def apply_params(req: ApplyParamsRequest):
    fd, temp_path = tempfile.mkstemp(suffix='.gjf', text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(req.content)
        new_lines = modify_gjf_content(
            temp_path, req.mem, req.nproc, req.keyword, req.charge, req.mult,
            chk_name=req.chk_name   # 传递chk名
        )
        new_content = ''.join(new_lines)
        return {"content": new_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


class RenameRequest(BaseModel):
    folder: str
    old_name: str
    new_name: str


@router.post("/rename")
async def rename_file(req: RenameRequest):
    if ".." in req.old_name or ".." in req.new_name:
        raise HTTPException(status_code=400, detail="非法文件名")
    old_path = os.path.join(req.folder, req.old_name)
    new_path = os.path.join(req.folder, req.new_name)
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="目标文件名已存在")
    try:
        os.rename(old_path, new_path)
        return {"message": "重命名成功", "new_name": req.new_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== WebSocket 批量修改（保留原有） ==========
from fastapi import WebSocket, WebSocketDisconnect
import json


@router.websocket("/modify")
async def gjf_modify_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        action = data.get("action")
        if action != "modify_gjf":
            await websocket.send_json({"type": "error", "message": "无效操作"})
            await websocket.close()
            return

        params = data.get("params", {})
        input_folder = params.get("input_folder")
        output_folder = params.get("output_folder")
        prefix = params.get("prefix", "")
        mem = params.get("mem", "20GB")
        nproc = params.get("nproc", "8")
        keyword = params.get("keyword", "#p opt b3lyp/6-31g(d,p)")
        charge = params.get("charge", "0")
        mult = params.get("mult", "1")
        # 支持文件列表
        files = params.get("files", None)

        if not input_folder or not os.path.isdir(input_folder):
            await websocket.send_json({"type": "error", "message": "输入文件夹不存在"})
            await websocket.close()
            return

        if not output_folder:
            output_folder = input_folder
        os.makedirs(output_folder, exist_ok=True)

        if files is None:
            gjf_files = glob.glob(os.path.join(input_folder, "*.gjf"))
        else:
            gjf_files = [os.path.join(input_folder, f) for f in files if f.endswith('.gjf')]

        if not gjf_files:
            await websocket.send_json({"type": "error", "message": "未找到 .gjf 文件"})
            await websocket.close()
            return

        total = len(gjf_files)
        for idx, gjf_path in enumerate(gjf_files):
            basename = os.path.basename(gjf_path)
            name, _ = os.path.splitext(basename)
            output_base = os.path.join(output_folder, f"{prefix}{name}")
            chk_name = f"{prefix}{name}.chk"
            try:
                new_lines = modify_gjf_content(
                    gjf_path, mem, nproc, keyword, charge, mult, chk_name=chk_name
                )
                output_path = output_base + ".gjf"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                await websocket.send_json({
                    "type": "progress",
                    "index": idx + 1,
                    "total": total,
                    "filename": basename,
                    "output": output_path,
                    "status": "success"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "progress",
                    "index": idx + 1,
                    "total": total,
                    "filename": basename,
                    "status": "error",
                    "message": str(e)
                })

        await websocket.send_json({"type": "done", "message": f"处理完成，共处理 {total} 个文件"})

    except WebSocketDisconnect:
        print("WebSocket 断开")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()


class BatchModifyRequest(BaseModel):
    input_folder: str
    output_folder: str
    files: list[str]
    prefix: str = ""
    mem: str = "20GB"
    nproc: str = "8"
    keyword: str = "#p opt b3lyp/6-31g(d,p)"
    charge: str = "0"
    mult: str = "1"


@router.post("/batch-modify")
async def batch_modify(req: BatchModifyRequest):
    """批量修改勾选的文件，输出到指定文件夹"""
    if not os.path.isdir(req.input_folder):
        raise HTTPException(status_code=400, detail="输入文件夹不存在")
    os.makedirs(req.output_folder, exist_ok=True)
    results = []
    for filename in req.files:
        original_path = os.path.join(req.input_folder, filename)
        if not os.path.exists(original_path):
            results.append({"filename": filename, "status": "error", "message": "文件不存在"})
            continue
        try:
            new_lines = modify_gjf_content(
                original_path, req.mem, req.nproc, req.keyword,
                req.charge, req.mult, chk_name=f"{req.prefix}{filename.replace('.gjf', '.chk')}"
            )
            output_path = os.path.join(req.output_folder, f"{req.prefix}{filename}")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            results.append({"filename": filename, "status": "success", "output": output_path})
        except Exception as e:
            results.append({"filename": filename, "status": "error", "message": str(e)})
    return {"results": results}
