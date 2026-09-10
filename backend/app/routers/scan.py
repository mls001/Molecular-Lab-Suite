# 提取扫描构象：从 ModRedundant 扫描 log（或任意多帧 log）逐帧生成 GJF
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.gjf_modifier import build_gjf_text
from app.core.log_parser import (
    _parse_orientation_blocks,
    _read_text,
    extract_modredundant_scan_steps,
    parse_log_text,
)

router = APIRouter()

MAX_STEPS = 2000


def _lines_and_name(path: Optional[str], content: Optional[str]):
    """读取 log 文本 → (lines, base_name)"""
    if content is not None:
        text = content
        name = 'scan'
    elif path:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
        if os.path.isdir(path):
            raise HTTPException(status_code=400, detail=f"这是一个文件夹而不是文件: {path}")
        text = _read_text(path)
        name = os.path.splitext(os.path.basename(path))[0]
    else:
        raise HTTPException(status_code=400, detail="缺少 path 或 content")
    return text.splitlines(), name


def _collect_steps(lines: list):
    """优先取 ModRedundant 扫描的收敛构象；否则退化为「所有坐标段」（任意多帧 log 可用）"""
    steps = extract_modredundant_scan_steps(lines)
    if steps:
        return [(int(sid), atoms, coords) for sid, atoms, coords in steps], 'ModRedundant'
    blocks = _parse_orientation_blocks(lines)
    rank = {'standard': 0, 'input': 1, 'z-matrix': 2}
    if blocks:
        best = min(rank.get(b['kind'], 9) for b in blocks)
        same = [b for b in blocks if rank.get(b['kind'], 9) == best]
        return ([(i + 1, b['atomic_numbers'], b['coords']) for i, b in enumerate(same)],
                'orientation')
    return [], ''


def _header_info(lines: list, name: str) -> dict:
    """关键词行 / 电荷 / 自旋：优先取 parse_log_text 的结果，再退化到输入回显"""
    info = {}
    try:
        info = parse_log_text('\n'.join(lines))
    except Exception:
        info = {}
    route = (info.get('route_first') or '').strip()
    if not route:                                  # 退化：第一行以 # 开头的内容
        for ln in lines:
            if ln.strip().startswith('#'):
                route = ln.strip()
                break
    charge = info.get('charge')
    mult = info.get('mult')
    if charge is None or mult is None:
        import re
        for ln in lines:
            m = re.search(r'Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(-?\d+)', ln, re.I)
            if m:
                charge, mult = int(m.group(1)), int(m.group(2))
        if charge is None or mult is None:
            for ln in lines:                       # 输入回显区的 "0 1"
                m = re.match(r'^\s*([-+]?\d+)\s+([-+]?\d+)\s*$', ln)
                if m:
                    charge, mult = int(m.group(1)), int(m.group(2))
                    break
    return {
        'name': name,
        'route': route or '#p opt b3lyp/6-31g(d,p)',
        'charge': 0 if charge is None else charge,
        'mult': 1 if mult is None else mult,
    }


class ScanRequest(BaseModel):
    path: Optional[str] = None
    content: Optional[str] = None
    step_ids: Optional[List[int]] = None      # 不填 = 全部
    prefix: str = ''
    route: Optional[str] = None               # 不填 = 用 log 中的关键词行
    mem: str = '20GB'
    nproc: str = '8'
    add_resources: bool = True
    charge: Optional[int] = None              # 不填 = 用 log 中的值
    mult: Optional[int] = None
    title: Optional[str] = None               # 不填 = 输出文件名（{基名}_ScanPoint{n}）


@router.post("/parse")
async def scan_parse(req: ScanRequest):
    """解析 log 中的扫描构象（只回传步骤编号与原子数，内容按需再取）"""
    lines, name = _lines_and_name(req.path, req.content)
    steps, source = _collect_steps(lines)
    if not steps:
        raise HTTPException(status_code=400,
                            detail='未找到扫描构象（既没有 ModRedundant 扫描步，也没有坐标段）')
    header = _header_info(lines, name)
    preview = [{'id': sid, 'natoms': len(atoms)} for sid, atoms, _coords in steps[:MAX_STEPS]]
    return {
        'ok': True,
        'name': name,
        'source': source,
        'count': len(preview),
        'truncated': len(steps) > MAX_STEPS,
        'steps': preview,
        'route': header['route'],
        'charge': header['charge'],
        'mult': header['mult'],
    }


def _select(steps, step_ids):
    if not step_ids:
        return steps
    wanted = set(int(x) for x in step_ids)
    picked = [s for s in steps if s[0] in wanted]
    if not picked:
        raise HTTPException(status_code=400, detail='所选步骤不存在')
    return picked


def _build_files(lines, name, req: ScanRequest):
    """按步骤生成 (id, filename, content)"""
    steps, _source = _collect_steps(lines)
    if not steps:
        raise HTTPException(status_code=400, detail='未找到扫描构象')
    steps = _select(steps, req.step_ids)
    if len(steps) > MAX_STEPS:
        raise HTTPException(status_code=400, detail=f'步骤过多（> {MAX_STEPS}），请分批提取')

    header = _header_info(lines, name)
    route = (req.route or '').strip() or header['route']
    charge = header['charge'] if req.charge is None else req.charge
    mult = header['mult'] if req.mult is None else req.mult

    files = []
    for sid, atomic_numbers, coords in steps:
        stem = f"{req.prefix}{name}_ScanPoint{sid}"
        filename = f"{stem}.gjf"
        content = build_gjf_text(
            mem=req.mem if req.add_resources else '20GB',
            nprocshared=req.nproc if req.add_resources else '8',
            keyword=route,
            charge=charge,
            mult=mult,
            atomic_numbers=atomic_numbers,
            coordinates=coords,
            title=req.title or stem,
            chk_name=f"{stem}.chk" if req.add_resources else None,
        )
        if not req.add_resources:
            # 与旧版一致：不添加资源行时，只保留关键词/标题/电荷与坐标
            kept = []
            for ln in content.splitlines():
                if ln.startswith('%mem=') or ln.startswith('%nprocshared=') or ln.startswith('%chk='):
                    continue
                kept.append(ln)
            content = '\n'.join(kept).lstrip('\n') + '\n'
        files.append({'id': sid, 'filename': filename, 'content': content,
                      'natoms': len(atomic_numbers)})
    return files, header


@router.post("/preview")
async def scan_preview(req: ScanRequest):
    """单步预览（用于界面展示，也用于远程逐帧上传）"""
    lines, name = _lines_and_name(req.path, req.content)
    step_ids = req.step_ids or []
    if not step_ids:
        steps, _s = _collect_steps(lines)
        if not steps:
            raise HTTPException(status_code=400, detail='未找到扫描构象')
        step_ids = [steps[0][0]]
    single = req.model_copy(update={'step_ids': step_ids[:1]}) if hasattr(req, 'model_copy') \
        else req.copy(update={'step_ids': step_ids[:1]})
    files, header = _build_files(lines, name, single)
    first = files[0]
    return {**first, 'route': header['route'], 'charge': header['charge'], 'mult': header['mult']}


@router.post("/build")
async def scan_build(req: ScanRequest):
    """批量生成内容（不落盘）：本地批量写盘或远程逐帧上传都用它"""
    lines, name = _lines_and_name(req.path, req.content)
    files, header = _build_files(lines, name, req)
    return {'files': files, 'count': len(files),
            'route': header['route'], 'charge': header['charge'], 'mult': header['mult']}


class ScanExtractRequest(ScanRequest):
    output_folder: str
    overwrite: bool = True


@router.post("/extract")
async def scan_extract(req: ScanExtractRequest):
    """批量写入 GJF 到输出目录"""
    lines, name = _lines_and_name(req.path, req.content)
    out_dir = (req.output_folder or '').replace('/', os.sep).replace('\\', os.sep)
    if not out_dir:
        raise HTTPException(status_code=400, detail='请选择输出目录')
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f'无法创建输出目录: {e}')

    files, header = _build_files(lines, name, req)
    results = []
    for item in files:
        path = os.path.join(out_dir, item['filename'])
        if os.path.exists(path) and not req.overwrite:
            results.append({'id': item['id'], 'filename': item['filename'],
                            'status': 'skipped', 'message': '已存在'})
            continue
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(item['content'])
            results.append({'id': item['id'], 'filename': item['filename'],
                            'status': 'success', 'output': path, 'natoms': item['natoms']})
        except Exception as e:                     # noqa: BLE001
            results.append({'id': item['id'], 'filename': item['filename'],
                            'status': 'error', 'message': str(e)})
    success = sum(1 for r in results if r['status'] == 'success')
    return {'results': results, 'count': len(results), 'success': success,
            'route': header['route'], 'charge': header['charge'], 'mult': header['mult']}
