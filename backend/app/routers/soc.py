# SOC（自旋轨道耦合）解析：ORCA "CALCULATED SOCME BETWEEN TRIPLETS AND SINGLETS"
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_COMPLEX3 = re.compile(
    r'^\s*(\d+)\s+(\d+)\s+'
    r'\(\s*([-+]?[\d.]+)\s*,\s*([-+]?[\d.]+)\s*\)\s*'
    r'\(\s*([-+]?[\d.]+)\s*,\s*([-+]?[\d.]+)\s*\)\s*'
    r'\(\s*([-+]?[\d.]+)\s*,\s*([-+]?[\d.]+)\s*\)'
)


def parse_soc_file(path: str) -> dict:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    lines = text.splitlines()

    # ---- 1) 单线态激发能（S1..Sn），基态 S0=0 eV ----
    singlet = {0: 0.0}
    for line in lines:
        m = re.search(r'STATE\s+(\d+):\s+E=\s*[-+]?[\d.]+ au\s+([-+]?[\d.]+)\s+eV', line, re.I)
        if m:
            singlet[int(m.group(1))] = float(m.group(2))

    # ---- 2) 三线态激发能：ORCA 用全局态号（可能从 11 开始）打印，需重排为 T1..Tn ----
    triplet = {}
    found = []
    for line in lines:
        mm = re.search(r'STATE\s+(\d+):\s+E=\s*[-+]?[\d.]+ au\s+([-+]?[\d.]+)\s+eV.*Mult\s+3', line, re.I)
        if mm:
            found.append((int(mm.group(1)), float(mm.group(2))))
    if found:
        found.sort(key=lambda x: x[0])
        for idx, (gid, ev) in enumerate(found, start=1):
            triplet[idx] = ev
    else:
        # 兜底：取 E[k] 每档的最后一个出现值
        tmp = {}
        for line in lines:
            mm = re.search(r'E\[\s*(\d+)\s*\]\s*=\s*[-+]?[\d.]+\s*\(.*?\)\s+([-+]?[\d.]+)\s+eV', line)
            if mm:
                tmp[int(mm.group(1))] = float(mm.group(2))
        if tmp:
            for k in range(1, 1 + max(tmp.keys())):
                if k - 1 in tmp:
                    triplet[k] = tmp[k - 1]

    # ---- 3) SOC 矩阵元（|Hso|，cm^-1）----
    # 行格式每行三个 (Re,Im) 复数，按分量平方和开根得到总强度
    soc = {}
    for line in lines:
        mm = _COMPLEX3.match(line)
        if not mm:
            continue
        t = int(mm.group(1))
        s = int(mm.group(2))
        nums = [float(mm.group(k)) for k in range(3, 9)]
        total = (sum(v * v for v in nums)) ** 0.5
        key = (t, s)
        # 若存在多块（cartesian / MS 分量），取强度较大的一块（信息更全）
        soc[key] = max(soc.get(key, 0.0), total)

    # ---- 4) 返回 ----

    return {
        'singlet': singlet,
        'triplet': triplet,
        'soc': {f'{t}_{s}': v for (t, s), v in soc.items()},
        'max_t': max((t for (t, s) in soc.keys()), default=0),
        'max_s': max((s for (t, s) in soc.keys()), default=0),
    }


class ParseRequest(BaseModel):
    path: str


@router.post("/api/soc/parse")
async def soc_parse(req: ParseRequest):
    try:
        with open(req.path, 'r', encoding='utf-8', errors='ignore') as f:
            f.read(64)
    except Exception:
        raise HTTPException(status_code=404, detail="文件不存在或无法读取")
    try:
        return parse_soc_file(req.path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
