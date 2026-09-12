"""外部程序（Multiwfn / VMD）目录检查

只做一件事：在用户选的目录（以及系统 PATH）里找可执行文件，告诉界面「找到了什么」。
后续与 Multiwfn / VMD 联用（调用其命令行做波函数分析、画图）时复用同一份目录配置。
"""
import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 各程序常见的可执行文件名（Windows / Linux / macOS）
CANDIDATES = {
    'multiwfn': ['Multiwfn.exe', 'Multiwfn', 'multiwfn.exe', 'multiwfn', 'Multiwfn_win.exe'],
    'vmd': ['vmd.exe', 'vmd', 'VMD', 'vmd_Win.exe', 'vmd_LINUXAMD64',
            os.path.join('bin', 'vmd.exe'), os.path.join('bin', 'vmd')],
    'tachyon': ['tachyon_WIN32.exe', 'tachyon.exe', 'tachyon_WIN64.exe', 'tachyon', 'tachyon_LINUXAMD64'],
}


def find_in_path(kind: str) -> str:
    """在系统 PATH（环境变量）里找可执行文件；找不到返回 ''"""
    for name in CANDIDATES.get(kind, []):
        p = shutil.which(name)
        if p and os.path.isfile(p):
            return p
    return ''


class ToolsCheckRequest(BaseModel):
    dir: str
    kind: str = 'multiwfn'                      # multiwfn | vmd | auto
    extra_names: Optional[List[str]] = None


@router.get("/kinds")
async def kinds():
    """支持联用的外部程序与候选可执行文件名"""
    return {'kinds': [{'id': k, 'names': v} for k, v in CANDIDATES.items()]}


@router.post("/check")
async def check_dir(req: ToolsCheckRequest):
    """检查目录里是否存在目标程序的可执行文件（顺便报告系统 PATH 里的情况）"""
    d = (req.dir or '').strip()
    if d and not os.path.isdir(d):
        raise HTTPException(status_code=400, detail=f'目录不存在: {d}')
    kind = (req.kind or 'multiwfn').lower()
    names = list(req.extra_names or [])
    if kind in CANDIDATES:
        names += CANDIDATES[kind]
    found, missing = [], []
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        path = os.path.join(d, name) if d else name
        if d and os.path.isfile(path):
            found.append({'name': name, 'path': path})
        else:
            missing.append(name)
    path_found = find_in_path(kind)
    return {'dir': d, 'kind': kind, 'found': found, 'ok': bool(found),
            'checked': len(seen), 'missing': missing[:6],
            'path_found': path_found, 'path_ok': bool(path_found)}
