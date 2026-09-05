from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import glob
import tempfile
from urllib.parse import unquote
from app.core.gjf_modifier import modify_gjf_content, build_gjf_text
from app.core.log_parser import parse_log_file, parse_log_text, _read_text
from typing import List, Optional
router = APIRouter()

LOG_EXTENSIONS = ('.log', '.out')


def _norm_dir(path: str) -> str:
    return unquote(path or '').replace('/', os.sep).replace('\\', os.sep)


def _base_name(filename: str) -> str:
    """去掉 .log/.out 等扩展名，得到基础文件名"""
    base = os.path.basename(filename or '')
    stem, ext = os.path.splitext(base)
    return stem if ext.lower() in LOG_EXTENSIONS else base


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


# ========== LOG → GJF（与修改 GJF 同页的 LOG 模式） ==========

@router.get("/log-list")
async def list_log_files(path: str):
    """列出目录下的 Gaussian 输出文件（.log / .out）"""
    folder = _norm_dir(path)
    if not os.path.isdir(folder):
        raise HTTPException(status_code=400, detail="无效目录")
    try:
        files = []
        with os.scandir(folder) as it:            # 不用 glob：避免 '[' 等通配符目录名出问题
            for entry in it:
                if entry.is_file() and entry.name.lower().endswith(LOG_EXTENSIONS):
                    files.append(entry.name)
        return {"files": sorted(set(files), key=str.lower)}
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"没有权限读取目录: {folder}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"读取目录失败: {e}")


class LogParseRequest(BaseModel):
    # 注意：这里必须写 Optional[str]，否则显式传 None 会被 Pydantic v2 判为校验错误
    path: Optional[str] = None       # 本地文件路径
    content: Optional[str] = None    # 或直接给文本（远程缓存内容）


def _read_log_text(path: str) -> str:
    """读取 LOG 文本（多编码兼容）；路径非法/无权限时给出明确错误"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
    if os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"这是一个文件夹而不是文件: {path}")
    try:
        return _read_text(path)
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"没有权限读取文件: {path}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {e}")


def _resolve_log_text(path: Optional[str] = None, content: Optional[str] = None) -> str:
    if content is not None:
        return content
    if not path:
        raise HTTPException(status_code=400, detail="缺少 path 或 content")
    return _read_log_text(path)


@router.post("/log-parse")
async def log_parse(req: LogParseRequest):
    """解析 LOG：末帧坐标、电荷/自旋、关键词行、收敛状态"""
    text = _resolve_log_text(req.path, req.content)
    try:
        info = parse_log_text(text)
    except Exception as e:                        # noqa: BLE001 - 解析异常也要以 JSON 形式回传
        raise HTTPException(status_code=400, detail=f"解析失败: {type(e).__name__}: {e}")
    if not info.get('ok'):
        raise HTTPException(status_code=400, detail=info.get('error') or '解析失败')
    return info


class LogToGjfRequest(BaseModel):
    path: Optional[str] = None
    content: Optional[str] = None
    filename: Optional[str] = None
    prefix: str = ""
    mem: str = "20GB"
    nproc: str = "8"
    keyword: str = "#p opt b3lyp/6-31g(d,p)"
    charge: str = "0"
    mult: str = "1"
    use_log_charge_mult: bool = True   # 电荷/自旋取用 LOG 中检测到的值
    use_log_keyword: bool = True       # 关键词行取用 LOG 中原始 route（默认沿用原任务方法）
    title: Optional[str] = None        # 不填则使用原 LOG 文件名作为标题行


def _build_from_info(info: dict, req: LogToGjfRequest, source_name: str) -> dict:
    """依据解析结果与参数生成 GJF 文本与文件名"""
    if not info.get('ok'):
        raise HTTPException(status_code=400, detail=info.get('error') or '解析失败')

    charge, mult = str(req.charge), str(req.mult)
    if req.use_log_charge_mult:
        if info.get('charge') is not None:
            charge = str(info['charge'])
        if info.get('mult') is not None:
            mult = str(info['mult'])

    keyword = (req.keyword or '').strip() or '#p opt b3lyp/6-31g(d,p)'
    if req.use_log_keyword and info.get('route_first'):
        keyword = info['route_first']

    out_name = req.filename or f"{req.prefix}{_base_name(source_name)}.gjf"
    if not out_name.lower().endswith('.gjf'):
        out_name = f"{_base_name(out_name)}.gjf"

    # 标题行使用原 LOG 文件名（不再从 LOG 文本里猜标题，避免取到 ITRead= 之类的内部行）
    title = req.title if req.title else _base_name(source_name)
    gjf_text = build_gjf_text(
        mem=req.mem, nprocshared=req.nproc, keyword=keyword, charge=charge, mult=mult,
        atomic_numbers=info['atomic_numbers'], coordinates=info['coords'],
        title=title, chk_name=out_name.replace('.gjf', '.chk').replace('.GJF', '.chk'),
    )
    return {
        "content": gjf_text,
        "filename": out_name,
        "charge": charge,
        "mult": mult,
        "keyword": keyword,
        "title": title,
        "log_title": info.get('title') or '',      # LOG 中检出的标题，仅供界面显示
        "info": info,
    }


@router.post("/log-to-gjf")
async def log_to_gjf(req: LogToGjfRequest):
    """单个 LOG → GJF（只生成内容，不落盘；由前端保存到输入/输出目录）"""
    text = _resolve_log_text(req.path, req.content)
    try:
        info = parse_log_text(text)
    except Exception as e:                        # noqa: BLE001 - 异常也要以 JSON 形式回传
        raise HTTPException(status_code=400, detail=f"解析失败: {type(e).__name__}: {e}")
    source_name = req.path or req.filename or 'output.log'
    return _build_from_info(info, req, source_name)


class LogBatchRequest(BaseModel):
    input_folder: str
    output_folder: str
    files: List[str] = []
    prefix: str = ""
    mem: str = "20GB"
    nproc: str = "8"
    keyword: str = "#p opt b3lyp/6-31g(d,p)"
    charge: str = "0"
    mult: str = "1"
    title: Optional[str] = None        # 不填则每个文件用各自的 LOG 文件名作标题行
    use_log_charge_mult: bool = True
    use_log_keyword: bool = True       # 默认沿用每个 LOG 各自的关键词
    overwrite: bool = True


@router.post("/log-batch")
async def log_batch(req: LogBatchRequest):
    """批量 LOG → GJF，直接写入输出目录"""
    input_folder = _norm_dir(req.input_folder)
    output_folder = _norm_dir(req.output_folder)
    if not os.path.isdir(input_folder):
        raise HTTPException(status_code=400, detail="输入文件夹不存在")
    try:
        os.makedirs(output_folder, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"无法创建输出目录: {e}")

    if req.files:
        log_files = [os.path.join(input_folder, f) for f in req.files]
    else:
        log_files = []
        with os.scandir(input_folder) as it:      # 不用 glob：避免 '[' 等通配符目录名出问题
            for entry in it:
                if entry.is_file() and entry.name.lower().endswith(LOG_EXTENSIONS):
                    log_files.append(entry.path)
        log_files = sorted(set(log_files), key=str.lower)

    if not log_files:
        raise HTTPException(status_code=400, detail="未找到 .log / .out 文件")

    results = []
    for log_path in log_files:
        basename = os.path.basename(log_path)
        if not os.path.exists(log_path):
            results.append({"filename": basename, "status": "error", "message": "文件不存在"})
            continue
        try:
            info = parse_log_file(log_path)
            if not info.get('ok'):
                results.append({"filename": basename, "status": "error",
                                "message": info.get('error') or '解析失败'})
                continue
            single = LogToGjfRequest(
                path=log_path, prefix=req.prefix, mem=req.mem, nproc=req.nproc,
                keyword=req.keyword, charge=req.charge, mult=req.mult, title=req.title,
                use_log_charge_mult=req.use_log_charge_mult,
                use_log_keyword=req.use_log_keyword,
            )
            built = _build_from_info(info, single, log_path)
            output_path = os.path.join(output_folder, built['filename'])
            if os.path.exists(output_path) and not req.overwrite:
                results.append({"filename": basename, "status": "skipped",
                                "message": "目标文件已存在", "output": output_path})
                continue
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(built['content'])
            results.append({
                "filename": basename,
                "status": "success",
                "output": output_path,
                "output_name": built['filename'],
                "natoms": info['natoms'],
                "charge": built['charge'],
                "mult": built['mult'],
                "frames": info['frames'],
                "took_last_frame_of": info['source'],
            })
        except Exception as e:                     # noqa: BLE001 - 单文件失败不影响整批
            results.append({"filename": basename, "status": "error", "message": str(e)})

    success = sum(1 for r in results if r['status'] == 'success')
    return {"results": results, "total": len(results), "success": success}


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
