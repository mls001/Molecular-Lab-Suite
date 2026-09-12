"""NTO 分析（sobereva.com/377）与空穴-电子分析（sobereva.com/434）

两者都是 Multiwfn 主功能 18 下的模块，脚本序列用真实 Multiwfn 2026.4.10 逐条验证：

NTO：  18 → 6 → <激发态输出文件> → <态序号> → 3(.mwfn 导出) → <导出路径> → 0 → q
        再对导出的 NTO 文件跑  200 → 3 → <占据数nocc>,<nocc+1> → <网格> → 1 → 0 → q
        （NTO 文件里占据 NTO 按本征值升序、空轨道按降序，所以贡献最大的一对
          恰好是 nocc 与 nocc+1 —— 与 sobereva.com/377 的尿嘧啶例子一致）

空穴-电子：18 → 1 → <激发态输出文件> → <态序号> → 1(算格点并输出各指标) → <网格>
        → 10/1(空穴)  11/1(电子)  12/2(Sr)或12/1(Sm)  13(跃迁密度)  15(CDD)  16(Chole/Cele)
        → 0 → 0 → 0 → q

所有导出都在目标目录里完成，产物按 <体系名>_S<态>_<种类>.cub 重命名，避免多态互相覆盖。
"""
import glob
import os
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.routers.ext import (_bmp_or_tga_to_png, _expected_cubes, _run, _run_multiwfn,
                             _tail, _tcl_path, annotate_png, cleanup_scratch, find_program,
                             move_product, product_dir, resolve_wavefn, safe_name, scan_source,
                             VMD_STYLES)

router = APIRouter()

# 空穴-电子导出选项 → Multiwfn 里要敲的按键
HE_EXPORTS = {
    'hole': ['10', '1'],          # 空穴分布（1 = 局域项 + 交叉项）
    'electron': ['11', '1'],      # 电子分布
    'Sr': ['12', '2'],            # 空穴-电子重叠（Sr，推荐）
    'Sm': ['12', '1'],            # 空穴-电子重叠（Sm）
    'transition': ['13'],         # 跃迁密度
    'CDD': ['15'],                # 密度差 ρ(ele) − ρ(hole)
    'CholeCele': ['16'],          # 平滑化的 Chole / Cele
}
HE_FILES = {'hole': 'hole.cub', 'electron': 'electron.cub', 'Sr': 'Sr.cub', 'Sm': 'Sm.cub',
            'CDD': 'CDD.cub', 'Chole': 'Chole.cub', 'Cele': 'Cele.cub',
            'transition': 'transition density.cub', 'transdens': 'transdens.cub'}


# ============ 解析 ============

def parse_state_summary(text: str) -> List[dict]:
    out = []
    for m in re.finditer(r'State:\s*(\d+)\s+Exc\. Energy:\s*(-?[\d.]+)\s*eV\s+Multi\.:\s*(\d+)'
                         r'\s+MO pairs:\s*(\d+)', text or ''):
        out.append({'state': int(m.group(1)), 'energy': float(m.group(2)),
                    'mult': int(m.group(3)), 'pairs': int(m.group(4))})
    return out


def parse_nocc(text: str) -> int:
    m = re.search(r'Orbitals from\s+1\s+to\s+(\d+)\s+are occupied', text or '')
    return int(m.group(1)) if m else 0


def _eig_block(text: str, header: str) -> List[float]:
    """取「The highest N eigenvalues of ... NTO pairs:」下面的一串本征值（可能分两行）"""
    m = re.search(header, text or '')
    if not m:
        return []
    out = []
    for line in text[m.end():].splitlines():
        s = line.strip()
        if not s:
            if out:
                break
            continue
        if s.lower().startswith('sum of'):
            break
        vals = re.findall(r'-?\d+\.\d+(?:[eE][+-]?\d+)?', s)
        if not vals:
            break
        out += [float(v) for v in vals]
    return out


def parse_nto_block(text: str) -> dict:
    """NTO 模块输出：激发能、本征值、归一化信息"""
    res = {'eigenvalues': [], 'alpha': [], 'beta': []}
    m = re.search(r'Excitation energy is\s+(-?[\d.]+)\s*eV', text or '')
    if m:
        res['energy'] = float(m.group(1))
    m = re.search(r'Multiplicity of this excited state is\s+(\d+)', text or '')
    if m:
        res['mult'] = int(m.group(1))
    res['eigenvalues'] = _eig_block(text, r'The highest \d+ eigenvalues of NTO pairs:')
    res['alpha'] = _eig_block(text, r'The highest \d+ eigenvalues of alpha NTO pairs:')
    res['beta'] = _eig_block(text, r'The highest \d+ eigenvalues of beta NTO pairs:')
    m = re.search(r'Sum of square of excitation coefficients:\s*(-?[\d.]+)', text or '')
    if m:
        res['exc_sum'] = float(m.group(1))
    m = re.search(r'Negative of the sum of square of de-excitation coefficients:\s*(-?[\d.]+)', text or '')
    if m:
        res['deexc_sum'] = float(m.group(1))
    m = re.search(r'Sum of above two values:\s*(-?[\d.]+)', text or '')
    if m:
        res['total_sum'] = float(m.group(1))
    m = re.search(r'Deviation to expected normalization value \(([\d.]+)\) is\s*(-?[\d.]+)', text or '')
    if m:
        res['expect'] = float(m.group(1))
        res['deviation'] = float(m.group(2))
    m = re.search(r'Sum of all(?: alpha and beta)? eigenvalues:\s*(-?[\d.]+)', text or '')
    if m:
        res['eigen_sum'] = float(m.group(1))
    return res


# 空穴-电子分析输出的定量指标（键, 中文标签, 单位, 正则）
HE_METRICS = [
    ('energy', '激发能', 'eV', r'Excitation energy of this state:\s*(-?[\d.]+)'),
    ('hole_integral', '空穴积分', '', r'Integral of hole:\s*(-?[\d.]+)'),
    ('electron_integral', '电子积分', '', r'Integral of electron:\s*(-?[\d.]+)'),
    ('Sr', 'Sr 指数（空穴-电子重叠）', '', r'Sr index \(integral of Sr function\):\s*(-?[\d.]+)'),
    ('Sm', 'Sm 指数（空穴-电子重叠）', '', r'Sm index \(integral of Sm function\):\s*(-?[\d.]+)'),
    ('D', 'D 指数（空穴-电子质心距离）', 'Å', r'D index:\s*(-?[\d.]+)'),
    ('delta_sigma', 'Δσ 指数（分布广度之差）', 'Å',
     r'Difference between RMSD of hole and electron \(delta sigma\):[\s\S]{0,200}?Overall:\s*(-?[\d.]+)'),
    ('H', 'H 指数（平均延展程度）', 'Å',
     r'H_CT:\s*-?[\d.]+\s+H index:\s*(-?[\d.]+)'),
    ('t', 't 指数（分离程度）', 'Å', r't index:\s*(-?[\d.]+)'),
    ('RMSD_hole', '空穴分布广度 |σ_hole|', 'Å', r'RMSD of hole in X/Y/Z:[\s\S]{0,80}?Norm:\s*(-?[\d.]+)'),
    ('RMSD_ele', '电子分布广度 |σ_ele|', 'Å',
     r'RMSD of electron in X/Y/Z:[\s\S]{0,80}?Norm:\s*(-?[\d.]+)'),
    ('HDI', '空穴离域指数 HDI', '', r'Hole delocalization index \(HDI\):\s*(-?[\d.]+)'),
    ('EDI', '电子离域指数 EDI', '', r'Electron delocalization index \(EDI\):\s*(-?[\d.]+)'),
    ('ghost', 'ghost-hunter 指数', 'eV', r'Ghost-hunter index:\s*(-?[\d.]+)'),
    ('dipole_change', '激发前后偶极变化 |Δμ|', 'a.u.',
     r'Variation of dipole moment with respect to ground state:[\s\S]{0,200}?Norm:\s*(-?[\d.]+)'),
]


def parse_he_metrics(text: str) -> List[dict]:
    rows = []
    for key, label, unit, pat in HE_METRICS:
        m = re.search(pat, text or '')
        if m:
            rows.append({'key': key, 'label': label, 'unit': unit, 'value': float(m.group(1))})
    for key, label in (('centroid_hole', '空穴质心'), ('centroid_ele', '电子质心')):
        m = re.search(r'Centroid of %s in X/Y/Z:\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)' %
                      ('hole' if key.endswith('hole') else 'electron'), text or '')
        if m:
            rows.append({'key': key, 'label': label, 'unit': 'Å',
                         'vec': [float(m.group(1)), float(m.group(2)), float(m.group(3))]})
    return rows


def parse_fresh_cubes(out_dir: str, before: dict) -> List[str]:
    """本次运行新写/改写的 .cub（mtime 严格变新，避免把上一轮的旧文件算进来）"""
    fresh = []
    for p in glob.glob(os.path.join(out_dir, '*.cub')):
        if p not in before or os.path.getmtime(p) > before[p] + 1e-6:
            fresh.append(p)
    return fresh


def snapshot_cubes(out_dir: str) -> dict:
    return {p: os.path.getmtime(p) for p in glob.glob(os.path.join(out_dir, '*.cub'))}


def _kind_of_cube(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0].strip().lower().replace('_', ' ')
    table = {'hole': 'hole', 'electron': 'electron', 'sr': 'Sr', 'sm': 'Sm', 'cdd': 'CDD',
             'chole': 'Chole', 'cele': 'Cele', 'transition density': 'transition',
             'transdens': 'transition', 'transition': 'transition'}
    return table.get(stem, stem)


def _rename_cube(path: str, stem: str, state: int, kind: str) -> str:
    """（旧接口保留：把 cube 改成 <体系名>_S<态>_<种类>.cub）"""
    d = os.path.dirname(path)
    ext = os.path.splitext(path)[1]
    new = os.path.join(d, f'{stem}_S{state}_{kind}{ext}')
    try:
        os.replace(path, new)
        return new
    except OSError:
        return path


# ============ 请求 ============

class AnalysisRequest(BaseModel):
    source: str                                   # 含激发态信息的输出文件（.out/.log）
    wavefn: str = ''                              # 参考态波函数（空 = 自动找同目录同名）
    out_dir: str = ''
    states: List[int] = [1]                       # 要分析的激发态序号
    grid: int = 2                                 # 1 低 / 2 中 / 3 高
    multiwfn_dir: str = ''
    multiwfn_exe: str = ''
    timeout: int = 3600


class NtoRequest(AnalysisRequest):
    export_format: str = 'mwfn'                   # mwfn | fch | molden
    pairs: int = 1                                # 生成贡献最大的前 N 对 NTO 的 cube（0 = 不生成）


class HoleElectronRequest(AnalysisRequest):
    exports: List[str] = ['hole', 'electron', 'Sr', 'CDD']
    centroids: bool = False                       # 叠加图里标出空穴/电子质心


def _prepare(req) -> tuple:
    """公共准备：路径/程序/波函数来源；产物目录固定为 <工作目录>/<分子文件名>/"""
    if not req.source or not os.path.isfile(req.source):
        raise HTTPException(status_code=404, detail=f'文件不存在: {req.source}')
    work_dir = req.out_dir or os.path.dirname(os.path.abspath(req.source))
    stem = safe_name(os.path.splitext(os.path.basename(req.source))[0])
    try:
        os.makedirs(work_dir, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f'无法创建目录: {e}')
    out_dir = product_dir(work_dir, stem)
    exe = req.multiwfn_exe or find_program(req.multiwfn_dir, 'multiwfn')
    if not exe or not os.path.isfile(exe):
        raise HTTPException(status_code=400, detail='没找到 Multiwfn 可执行文件，请先在右上角「外部程序」里配置目录')
    src, notes, info = resolve_wavefn(req.source, req.wavefn, False, [work_dir])
    notes.append(f'[提示] 波函数来源：{src}')
    notes.append(f'[提示] 产物目录：{out_dir}')
    return src, out_dir, exe, notes, info


def _states_of(req) -> List[int]:
    states = sorted({int(s) for s in (req.states or []) if int(s) > 0})
    if not states:
        raise HTTPException(status_code=400, detail='请先选择激发态')
    return states[:20]


# ============ NTO 分析 ============

@router.post("/nto")
async def nto_analysis(req: NtoRequest):
    """NTO 分析（sobereva.com/377）：输出本征值 + 可选导出 NTO 并生成前 N 对轨道 cube"""
    src, out_dir, exe, notes, info = _prepare(req)
    states = _states_of(req)
    fmt = (req.export_format or 'mwfn').lower()
    fmt_key = {'molden': '1', 'fch': '2', 'mwfn': '3'}.get(fmt, '3')
    fmt_ext = {'1': '.molden', '2': '.fch', '3': '.mwfn'}[fmt_key]
    base = safe_name(os.path.splitext(os.path.basename(req.source))[0])
    logs, results = [], []
    for st in states:
        nto_file = os.path.join(out_dir, f'{base}-S{st}{fmt_ext}')
        if os.path.isfile(nto_file):
            try:
                os.remove(nto_file)                # 先删掉上一轮的，才能确认这次真的导出了
            except OSError:
                pass
        script = ['18', '6', req.source, str(st), fmt_key, nto_file, '0', 'q']
        code, out, _fresh = _run_multiwfn(exe, src, out_dir, script,
                                          f'_mls_nto_S{st}.txt', req.timeout)
        parsed = parse_nto_block(out)
        nocc = parse_nocc(out)
        states_info = parse_state_summary(out)
        cur = next((s for s in states_info if s['state'] == st), {})
        parsed.update({'state': st, 'nocc': nocc,
                       'energy': parsed.get('energy', cur.get('energy')),
                       'mult': parsed.get('mult', cur.get('mult')),
                       'pairs': cur.get('pairs', 0)})
        # 自旋：先按文件顺序号查（ORCA 的 S/T 重复编号时最可靠），再退回 Multiwfn 打印的多重度
        spin = _spin_of_order(req.source, st) \
            or ('T' if parsed.get('mult') == 3 else ('S' if parsed.get('mult') == 1 else _spin_of(out, st)))
        item = {'state': st, 'ok': os.path.isfile(nto_file) and os.path.getsize(nto_file) > 0,
                'spin': spin,
                'nto_file': nto_file if os.path.isfile(nto_file) else '',
                'parsed': parsed, 'cubes': [], 'error': ''}
        if not item['ok']:
            item['error'] = _diagnose_analysis(out, code)
        logs.append(f'--- NTO 分析 S{st}（返回码 {code}）{item["error"]} ---\n{_tail(out, 14)}')
        # 生成贡献最大的前 N 对 NTO 的 cube：占据侧 nocc, nocc-1…，空轨道侧 nocc+1, nocc+2…
        want = max(0, int(req.pairs or 0))
        if item['ok'] and want and nocc:
            idxs = []
            for k in range(want):
                idxs += [nocc - k, nocc + 1 + k]
            idxs = sorted({i for i in idxs if i > 0})
            before = snapshot_cubes(out_dir)
            script2 = ['200', '3', ','.join(str(i) for i in idxs), str(req.grid), '1', '0', 'q']
            code2, out2, fresh = _run_multiwfn(exe, nto_file, out_dir, script2,
                                               f'_mls_ntocub_S{st}.txt', req.timeout)
            by_name = {os.path.basename(p).lower(): p for p in fresh}
            eig = parsed.get('eigenvalues') or []
            for k in range(want):
                for side, idx in (('occ', nocc - k), ('vir', nocc + 1 + k)):
                    if idx <= 0:
                        continue
                    hit = next((by_name[n.lower()] for n in _expected_cubes(idx) if n.lower() in by_name), '')
                    if not hit:
                        continue
                    # 命名：<分子名>-S<态>-NTO<序号>-<H 占据 / E 空>-<贡献值>
                    val = eig[k] if k < len(eig) else None
                    side_tag = 'H' if side == 'occ' else 'E'
                    contrib = f'-{val * 100:.1f}' if val is not None else ''
                    cub = move_product(hit, out_dir, f'{base}-S{st}-NTO{idx}-{side_tag}{contrib}.cub')
                    item['cubes'].append({
                        'index': idx, 'side': side, 'cub': cub, 'name': os.path.basename(cub),
                        'eigen': val, 'contrib': (val * 100 if val is not None else None),
                        'pair': f'{min(nocc - k, nocc + 1 + k)}/{max(nocc - k, nocc + 1 + k)}',
                        'label': f'NTO{idx}（{"Hole" if side == "occ" else "Electron"}）'})
            logs.append(f'--- NTO 轨道 cube S{st}（返回码 {code2}）：{len(item["cubes"])} 个 ---\n'
                        f'{_tail(out2, 8)}')
        results.append(item)
    ok = any(r['ok'] for r in results)
    hint = '' if ok else (results[0]['error'] if results and results[0]['error'] else
                          'NTO 分析失败，请看下方日志')
    return {'ok': ok, 'out_dir': out_dir, 'source': src, 'items': results, 'states': states,
            'log': '\n'.join(notes + logs), 'hint': hint}


def _spin_of(text: str, state: int) -> str:
    """这个激发态是单重态(S)还是三重态(T)（Gaussian 的对称性标签 / ORCA 的 Mult 或区块标题）

    注意：ORCA 的 SOC 输出里单重态与三重态各自从 1 编号，同一序号可能对应两种自旋，
    这时以文件里第一个出现的为准（NTO 分析另有 Multiwfn 打印的 Multiplicity 更可靠）。
    """
    m = re.search(r'Excited State\s+%d:\s+(\S+)' % state, text or '')
    if m:
        sym = m.group(1).lower()
        if sym.startswith('triplet'):
            return 'T'
        if sym.startswith('singlet'):
            return 'S'
    spin = ''
    for line in (text or '').splitlines():
        up = line.upper()
        if 'EXCITED STATES' in up and 'SINGLET' in up:
            spin = 'S'
        elif 'EXCITED STATES' in up and 'TRIPLET' in up:
            spin = 'T'
        if re.match(r'^STATE\s+%d:\s' % state, line.strip()):
            mm = re.search(r'Mult\s+(\d+)', line)
            if mm:
                return 'T' if int(mm.group(1)) == 3 else 'S'
            return spin
    return ''


def _spin_of_order(source: str, state: int) -> str:
    """按「文件顺序号」判断该激发态的自旋（ORCA 的 S/T 各自编号时，序号会重复，只能按顺序取）"""
    try:
        with open(source, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    except OSError:
        return ''
    states, _kind = parse_excited_states(text)
    for st in states:
        if st.get('order') == state:
            return st.get('spin') or ''
    return ''


def _diagnose_analysis(out: str, code: int) -> str:
    low = (out or '').lower()
    if 'no basis function information' in low:
        return '缺少基组信息：Gaussian 需加 pop=full gfinput，或改用 .fch/.fchk 波函数文件'
    if 'cannot find' in low and 'orbital' in low:
        return 'Multiwfn 读不到激发态信息：请确认该文件是 TD/CIS 任务的输出（含 IOp(9/40=4)）'
    if 'forrtl' in low or 'severe (' in low:
        return 'Multiwfn 异常退出（输入脚本与程序提示不匹配）：可在「编辑脚本模板」里按版本调整'
    if 'no excited state information' in low or 'error while reading' in low:
        return '该文件里没有激发态信息，无法做电子激发分析'
    if code != 0:
        return f'Multiwfn 返回码 {code}，未得到结果（见日志）'
    return ''


# ============ 空穴-电子分析 ============

def _he_script(source: str, state: int, grid: int, exports: List[str]) -> List[str]:
    keys = [k for k in HE_EXPORTS if k in (exports or [])]
    if 'Sm' in keys and 'Sr' in keys:
        keys.remove('Sm')                          # 同时选两个没意义，优先 Sr
    lines = ['18', '1', source, str(state), '1', str(grid)]
    for k in keys:
        lines += HE_EXPORTS[k]
    lines += ['0', '0', '0', 'q']                  # 后处理 → 空穴-电子 → 激发分析 → 主菜单
    return lines


@router.post("/hole-electron")
async def hole_electron(req: HoleElectronRequest):
    """空穴-电子分析（sobereva.com/434）：定量指标 + 空穴/电子/重叠/CDD/Chole/Cele 的 cube"""
    src, out_dir, exe, notes, info = _prepare(req)
    states = _states_of(req)
    base = safe_name(os.path.splitext(os.path.basename(req.source))[0])
    logs, results = [], []
    for st in states:
        before = snapshot_cubes(out_dir)
        script = _he_script(req.source, st, req.grid, req.exports)
        code, out, _fresh = _run_multiwfn(exe, src, out_dir, script,
                                          f'_mls_he_S{st}.txt', req.timeout)
        metrics = parse_he_metrics(out)
        fresh = parse_fresh_cubes(out_dir, before)
        cubes = []
        for p in fresh:
            kind = _kind_of_cube(p)
            if os.path.getsize(p) == 0:            # Multiwfn 中断时会留下 0 字节文件
                try:
                    os.remove(p)
                except OSError:
                    pass
                continue
            # 命名：<分子名>-S<态>-<hole/electron/Sr/CDD/Chole/Cele>
            cub = move_product(p, out_dir, f'{base}-S{st}-{kind}.cub')
            cubes.append({'kind': kind, 'cub': cub, 'name': os.path.basename(cub)})
        cur = next((s for s in parse_state_summary(out) if s['state'] == st), {})
        item = {'state': st, 'ok': bool(metrics) and bool(cubes),
                'spin': _spin_of_order(req.source, st) or _spin_of(out, st),
                'metrics': metrics, 'cubes': cubes, 'pairs': cur.get('pairs', 0), 'error': ''}
        if not item['ok']:
            item['error'] = _diagnose_analysis(out, code)
        logs.append(f'--- 空穴-电子分析 S{st}（返回码 {code}，{len(cubes)} 个 cube）'
                    f'{item["error"]} ---\n{_tail(out, 14)}')
        results.append(item)
    ok = any(r['ok'] for r in results)
    hint = '' if ok else (results[0]['error'] if results and results[0]['error'] else
                          '空穴-电子分析失败，请看下方日志')
    return {'ok': ok, 'out_dir': out_dir, 'source': src, 'items': results, 'states': states,
            'log': '\n'.join(notes + logs), 'hint': hint}


# ============ 叠加图（空穴+电子 / Chole+Cele） ============

OVERLAY_PROC = """proc mls_overlay {cub1 cub2 scene w h iso transparent spheres} {
  mol delete all
  color Display Background white
  display depthcue off
  axes location Off
  color Name C tan
  color change rgb tan 0.700000 0.560000 0.360000
  material change mirror Opaque 0.15
  material change outline Opaque 4.000000
  material change outlinewidth Opaque 0.5
  material change ambient Glossy 0.1
  material change diffuse Glossy 0.600000
  material change opacity Glossy 0.75
  material change shininess Glossy 1.0
  light 3 on
  if {$cub1 ne ""} {
    mol new $cub1 type cube
    mol modstyle 0 top CPK 0.800000 0.300000 22.000000 22.000000
    mol addrep top
    mol modstyle 1 top Isosurface $iso 0 0 0 1 1
    mol modcolor 1 top ColorID 12
    mol modmaterial 1 top Glossy
  }
  if {$cub2 ne ""} {
    mol new $cub2 type cube
    mol modstyle 0 top CPK 0.800000 0.300000 22.000000 22.000000
    mol addrep top
    mol modstyle 1 top Isosurface $iso 0 0 0 1 1
    mol modcolor 1 top ColorID 22
    mol modmaterial 1 top Glossy
  }
  if {$transparent} {
    material change opacity Glossy 0.40
    material change ambient Glossy 0.25
  }
  foreach s $spheres {
    draw color [lindex $s 3]
    draw sphere [list [lindex $s 0] [lindex $s 1] [lindex $s 2]] radius 0.25 resolution 20
  }
  display distance -7.0
  display height 10
  display resize $w $h
  render Tachyon $scene
}
"""


class OverlayRequest(BaseModel):
    out_dir: str
    folder_name: str = ''             # 归档子目录名（默认取 cube 所在目录名）
    pairs: List[dict] = []            # [{label, cub1, cub2?, note?, spheres?}]
    size: List[int] = []
    iso: float = 0.02
    style: str = 'art'
    transparent: bool = False         # 等值面半透明（Cele/Chole 要看见质心点时打开）
    centroids: bool = False           # 用 pair 里的 chole/cele 画质心球
    vmd_dir: str = ''
    vmd_exe: str = ''
    tachyon: Optional[List[str]] = None
    timeout: int = 1800


@router.post("/overlay")
async def overlay(req: OverlayRequest):
    """把 cube 画成图（可两张叠加），支持半透明等值面与质心标注（空穴绿 + 电子蓝）

    pairs 里 cub2 可以不给（只画一张）；spheres 是 [[x,y,z,color], ...] 的球列表。
    """
    pairs = [p for p in req.pairs if p.get('cub1') and os.path.isfile(p['cub1'])]
    if not pairs:
        raise HTTPException(status_code=400, detail='没有可渲染的 cube 文件')
    work_dir = req.out_dir or os.path.dirname(pairs[0]['cub1'])
    folder = safe_name(req.folder_name or os.path.basename(work_dir.rstrip('\\/')))
    out_dir = product_dir(work_dir, folder)
    exe = req.vmd_exe or find_program(req.vmd_dir, 'vmd')
    if not exe or not os.path.isfile(exe):
        raise HTTPException(status_code=400, detail='没找到 VMD 可执行文件，请先在右上角「外部程序」里配置目录')
    vmd_dir = os.path.dirname(exe)
    tachyon_exe = ''
    for name in ('tachyon_WIN32.exe', 'tachyon.exe', 'tachyon_WIN64.exe', 'tachyon'):
        p = os.path.join(vmd_dir, name)
        if os.path.isfile(p):
            tachyon_exe = p
            break
    if not tachyon_exe:
        from app.routers.tools import find_in_path
        tachyon_exe = find_in_path('tachyon')
    style_lines, style_tachyon, style_size = VMD_STYLES.get(req.style, VMD_STYLES['art'])
    w, h = (req.size or list(style_size))[:2]
    tpl_t = req.tachyon or style_tachyon
    jobs, results, logs = [], [], []
    for i, p in enumerate(pairs[:24]):
        stem = safe_name(p.get('label') or f'overlay{i + 1}', f'overlay{i + 1}')
        # 质心球：显式给的 spheres 优先；否则按 centroids 开关用 chole/cele（紫=空穴、橙=电子）
        spheres = []
        for s in (p.get('spheres') or []):
            if isinstance(s, (list, tuple)) and len(s) >= 3:
                spheres.append([s[0], s[1], s[2], (s[3] if len(s) > 3 else 'purple')])
        if req.centroids:
            ch, ce = p.get('chole'), p.get('cele')
            if ch:
                spheres.append([ch[0], ch[1], ch[2], 'purple'])
            if ce:
                spheres.append([ce[0], ce[1], ce[2], 'orange'])
        jobs.append({'label': stem, 'cub1': p['cub1'], 'cub2': p.get('cub2') or '',
                     'note': p.get('note') or '', 'spheres': spheres,
                     'scene': os.path.join(out_dir, f'_mls_{stem}.dat'),
                     'bmp': os.path.join(out_dir, f'_mls_{stem}.bmp'),
                     'png': os.path.join(out_dir, f'{stem}.png')})
    lines = [OVERLAY_PROC]
    for j in jobs:
        sph = ' '.join('{{{0} {1} {2} {3}}}'.format(s[0], s[1], s[2], s[3]) for s in j['spheres'])
        lines.append('mls_overlay {{{0}}} {{{1}}} {2} {3} {4} {5} {6} {{{7}}}'.format(
            _tcl_path(j['cub1']), _tcl_path(j['cub2']), os.path.basename(j['scene']),
            w, h, req.iso, 1 if req.transparent else 0, sph))
    lines.append('quit')
    script_path = os.path.join(out_dir, '_mls_overlay.vmd')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    code, out = _run([exe, '-dispdev', 'text', '-e', script_path, '-eofexit'], out_dir,
                     timeout=req.timeout)
    logs.append(f'--- VMD 叠加渲染（返回码 {code}）---\n{_tail(out, 12)}')
    for j in jobs:
        made = ''
        if tachyon_exe and os.path.isfile(j['scene']):
            # tachyon 用相对文件名（它处理不了带空格的绝对路径，会静默不写文件）
            args = [tachyon_exe] + [str(a).replace('{scene}', os.path.basename(j['scene']))
                                    .replace('{bmp}', os.path.basename(j['bmp']))
                                    .replace('{w}', str(w)).replace('{h}', str(h)) for a in tpl_t]
            code2, out2 = _run(args, out_dir, timeout=req.timeout)
            logs.append(f'--- tachyon {j["label"]}（返回码 {code2}）---\n{_tail(out2, 6)}')
            if os.path.isfile(j['bmp']) and _bmp_or_tga_to_png(j['bmp'], j['png']):
                made = j['png']
        if made and j['note']:
            annotate_png(made, j['note'])           # 右下角标注（D 指数 / Sr 等）
        results.append({'label': j['label'], 'ok': bool(made), 'image': made,
                        'name': os.path.basename(made) if made else '', 'note': j['note']})
    if all(r['ok'] for r in results):
        cleanup_scratch(out_dir)
    return {'ok': all(r['ok'] for r in results), 'out_dir': out_dir, 'items': results,
            'log': '\n'.join(logs)}


# ============ 激发态列表（不调用 Multiwfn，只看输出文件） ============

def parse_excited_states(text: str):
    """从输出文件文本里列出激发态（Gaussian / ORCA），带自旋标签与独立编号

    Gaussian:  Excited State   1:      Singlet-A      4.7970 eV  258.49 nm  f=0.0000
               Excited State   1:      Triplet-A      3.1234 eV  ...
    ORCA:      TD-DFT EXCITED STATES (SINGLETS) / (TRIPLETS) 区块下的
               STATE  1:  E=   0.125128 au      3.405 eV    27462.3 cm**-1 <S**2> = 0.000000 Mult 1

    每条都带：
      state      文件里的原始序号（ORCA 的 S/T 会各自从头编号，可能重复）
      order      文件顺序（1、2、3…，全局唯一，交给 Multiwfn 用这个）
      spin       'S' / 'T'
      spin_index 该自旋内的编号（S1、S2、T1、T2…，界面显示用）
    """
    states, kind = [], ''

    def finish(kind_name):
        s_ct = t_ct = 0
        for i, st in enumerate(states):
            st['order'] = i + 1
            if st['spin'] == 'T':
                t_ct += 1
                st['spin_index'] = t_ct
            else:
                s_ct += 1
                st['spin_index'] = s_ct
        return states, kind_name

    for m in re.finditer(r'Excited State\s+(\d+):\s+(\S+)\s+(-?[\d.]+)\s*eV\s+([\d.]+)\s*nm\s+f=([\d.]+)',
                         text or ''):
        kind = kind or 'gaussian'
        sym = m.group(2)
        low = sym.lower()
        spin = 'T' if low.startswith('triplet') else ('S' if low.startswith('singlet') else '')
        states.append({'state': int(m.group(1)), 'sym': sym, 'spin': spin,
                       'mult': 3 if spin == 'T' else (1 if spin == 'S' else 0),
                       'energy': float(m.group(3)), 'nm': float(m.group(4)), 'f': float(m.group(5))})
    if states:
        return finish(kind)
    spin_ctx = ''
    for line in (text or '').splitlines():
        up = line.upper()
        if 'EXCITED STATES' in up and 'SINGLET' in up:
            spin_ctx = 'S'
        elif 'EXCITED STATES' in up and 'TRIPLET' in up:
            spin_ctx = 'T'
        m = re.match(r'^STATE\s+(\d+):\s+E=\s*(-?[\d.]+)\s*au\s+(-?[\d.]+)\s*eV\s+'
                     r'([\d.]+)\s*(nm|cm\*\*-1)(.*)$', line.strip())
        if not m:
            continue
        kind = kind or 'orca'
        rest = m.group(6) or ''
        mm = re.search(r'Mult\s+(\d+)', rest)
        mult = int(mm.group(1)) if mm else (3 if spin_ctx == 'T' else (1 if spin_ctx == 'S' else 0))
        ff = re.search(r'f=\s*([\d.]+)', rest)
        states.append({'state': int(m.group(1)),
                       'sym': ('Triplet' if spin_ctx == 'T' else ('Singlet' if spin_ctx == 'S' else '')),
                       'spin': 'T' if mult == 3 else ('S' if mult == 1 else spin_ctx),
                       'mult': mult, 'energy': float(m.group(3)),
                       'nm': float(m.group(4)) if m.group(5) == 'nm' else 0.0,
                       'f': float(ff.group(1)) if ff else 0.0})
    return finish(kind)


@router.get("/states")
async def excited_states(path: str = '', wavefn: str = ''):
    """从输出文件里直接列出激发态（Gaussian / ORCA），供界面勾选；顺便预检波函数文件"""
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f'文件不存在: {path}')
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    except OSError as e:
        raise HTTPException(status_code=400, detail=f'读取文件失败: {e}')
    states, kind = parse_excited_states(text)
    wf = scan_source(wavefn) if (wavefn and os.path.isfile(wavefn)) else None
    hint = ''
    if not states:
        hint = ('这个文件里没有找到激发态信息：请用 TD/CIS 任务（Gaussian 加 td 与 IOp(9/40=4)，'
                'ORCA 用 %tddft 并保留 .molden/.gbw）')
    return {'path': path, 'kind': kind, 'states': states, 'wavefn': wf, 'hint': hint}
