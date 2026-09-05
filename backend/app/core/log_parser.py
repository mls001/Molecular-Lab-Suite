import os
import re
import numpy as np
import pandas as pd


def parse_orbital_energies_advanced(log_path: str) -> dict:
    """从高斯 log 文件提取轨道能量"""
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    def find_last_title(pattern):
        for i in range(len(lines) - 1, -1, -1):
            if re.search(pattern, lines[i], re.I):
                return i
        return None

    def extract_energies_from_line(line):
        nums = re.findall(r'[-+]?\d*\.?\d+(?:[DdEe][-+]?\d+)?', line)
        energies = []
        for num_str in nums:
            num_str = num_str.replace('D', 'E').replace('d', 'E')
            try:
                energies.append(float(num_str))
            except ValueError:
                continue
        return energies

    def collect_continuous_upward(start_idx, pattern):
        rows = []
        i = start_idx
        while i >= 0 and re.search(pattern, lines[i], re.I):
            rows.append(i)
            i -= 1
        rows.reverse()
        return rows

    alpha_occ_pos = find_last_title(r'Alpha\s+occ\.?\s+eigenvalues\s*--')
    alpha_occ_energies = []
    if alpha_occ_pos is not None:
        rows = collect_continuous_upward(alpha_occ_pos, r'Alpha\s+occ\.?\s+eigenvalues\s*--')
        for idx in rows:
            alpha_occ_energies.extend(extract_energies_from_line(lines[idx]))

    alpha_virt_pos = find_last_title(r'Alpha\s+virt\.?\s+eigenvalues\s*--')
    alpha_virt_energies = []
    if alpha_virt_pos is not None:
        rows = collect_continuous_upward(alpha_virt_pos, r'Alpha\s+virt\.?\s+eigenvalues\s*--')
        for idx in rows:
            alpha_virt_energies.extend(extract_energies_from_line(lines[idx]))

    beta_occ_pos = find_last_title(r'Beta\s+occ\.?\s+eigenvalues\s*--')
    beta_occ_energies = []
    if beta_occ_pos is not None:
        rows = collect_continuous_upward(beta_occ_pos, r'Beta\s+occ\.?\s+eigenvalues\s*--')
        for idx in rows:
            beta_occ_energies.extend(extract_energies_from_line(lines[idx]))

    beta_virt_pos = find_last_title(r'Beta\s+virt\.?\s+eigenvalues\s*--')
    beta_virt_energies = []
    if beta_virt_pos is not None:
        rows = collect_continuous_upward(beta_virt_pos, r'Beta\s+virt\.?\s+eigenvalues\s*--')
        for idx in rows:
            beta_virt_energies.extend(extract_energies_from_line(lines[idx]))

    # RHF 后备
    if not alpha_occ_energies:
        rhf_occ_pos = find_last_title(r'Occupied\s*\(RHF\)\s*--')
        if rhf_occ_pos is not None:
            rows = collect_continuous_upward(rhf_occ_pos, r'Occupied\s*\(RHF\)\s*--')
            for idx in rows:
                alpha_occ_energies.extend(extract_energies_from_line(lines[idx]))
    if not alpha_virt_energies:
        rhf_virt_pos = find_last_title(r'Virtual\s*\(RHF\)\s*--')
        if rhf_virt_pos is not None:
            rows = collect_continuous_upward(rhf_virt_pos, r'Virtual\s*\(RHF\)\s*--')
            for idx in rows:
                alpha_virt_energies.extend(extract_energies_from_line(lines[idx]))

    alpha_occ = [(i + 1, eng) for i, eng in enumerate(alpha_occ_energies)]
    alpha_virt = [(i + 1 + len(alpha_occ_energies), eng) for i, eng in enumerate(alpha_virt_energies)]
    beta_occ = [(i + 1, eng) for i, eng in enumerate(beta_occ_energies)]
    beta_virt = [(i + 1 + len(beta_occ_energies), eng) for i, eng in enumerate(beta_virt_energies)]

    homo_alpha = alpha_occ[-1][0] if alpha_occ else None
    lumo_alpha = alpha_virt[0][0] if alpha_virt else None
    homo_beta = beta_occ[-1][0] if beta_occ else None
    lumo_beta = beta_virt[0][0] if beta_virt else None

    return {
        'filename': os.path.basename(log_path),
        'alpha_occ': alpha_occ,
        'alpha_virt': alpha_virt,
        'beta_occ': beta_occ,
        'beta_virt': beta_virt,
        'homo_alpha': homo_alpha,
        'lumo_alpha': lumo_alpha,
        'homo_beta': homo_beta,
        'lumo_beta': lumo_beta,
    }


def _read_text(path: str) -> str:
    """按多种编码尝试读取文本文件（Gaussian 输出可能是 GBK/UTF-8/带 BOM）"""
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'latin-1'):
        try:
            with open(path, 'r', encoding=enc, errors='ignore') as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


_LOG_ORIENT_RE = re.compile(r'^\s*(Standard|Input|Z-Matrix)\s+orientation\s*:', re.IGNORECASE)
# 兼容定点与小/大数的 D/E 指数写法，例如 -0.123456D-05
_LOG_NUM = r'[-+]?\d*\.?\d+(?:[DdEe][-+]?\d+)?'
_LOG_COORD_RE = re.compile(
    rf'^\s*\d+\s+(\d+)\s+\d+\s+({_LOG_NUM})\s+({_LOG_NUM})\s+({_LOG_NUM})'
)
_LOG_CHARGE_RE = re.compile(r'Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(-?\d+)', re.IGNORECASE)
_LOG_ROUTE_RE = re.compile(r'^\s*#')


def _to_float(token: str) -> float:
    return float(token.replace('D', 'E').replace('d', 'e'))


def _parse_orientation_blocks(lines: list) -> list:
    """扫描全部坐标段，返回 [{kind, line, atomic_numbers, coords}, ...]（按出现顺序）"""
    blocks = []
    i, n = 0, len(lines)
    while i < n:
        m = _LOG_ORIENT_RE.match(lines[i])
        if not m:
            i += 1
            continue
        kind = m.group(1).lower()
        atomic_numbers, coords = [], []
        j = i + 1
        while j < n and j < i + 500:
            cm = _LOG_COORD_RE.match(lines[j])
            if cm:
                atomic_numbers.append(int(cm.group(1)))
                coords.append((_to_float(cm.group(2)), _to_float(cm.group(3)), _to_float(cm.group(4))))
                j += 1
                continue
            if atomic_numbers:      # 已读到坐标，遇到其它行即本段结束
                break
            j += 1                  # 跳过表头/分隔线
        if atomic_numbers:
            blocks.append({
                'kind': kind,
                'line': i,
                'atomic_numbers': atomic_numbers,
                'coords': coords,
            })
        i = j if j > i else i + 1
    return blocks


_BASIS_RE = re.compile(
    r'^(sto-?\d+g?|3-21g|4-31g|6-31g|6-311g|6-31\+|6-311\+|cc-pv|aug-cc-pv|def2|lanl2dz|lanl2mb'
    r'|sdd|shf|dz|dzp|tz|tzp|tzvp|qzv|qzvp|midix|minix|sv|svp|pcseg|aug-|may-|jul-|dkh)',
    re.IGNORECASE,
)
_FUNCTIONAL_RE = re.compile(
    r'^(hf|b3lyp|b3pw91|b3p86|b1lyp|mpw1pw91|mpw1k|pbe0|pbe1pbe|pbe|bp86|blyp|b97d|b97-d|tpss|tpssh'
    r'|m06l|m06-2x|m062x|m06|m08hx|m05-2x|m052x|m05|wb97x|wb97xd|wb97x-d|cam-b3lyp|lc-wpbe|lc-blyp'
    r'|apfd|apbe|mn15|mn12|svwn|olyp|vsxc|hse06|pbesol|mp2|mp4|ccsd|qcisd|b2plyp|b2gp-plyp|pw6b95'
    r'|pwpb95|sogga11x|n12|revm06|revtpss|bmk)(\b|$)',
    re.IGNORECASE,
)


def split_route(route: str) -> dict:
    """把关键词行拆成 计算模式 / 泛函 / 基组，便于回填到修改 GJF 页面的参数栏。

    支持两种常见写法：
      "#p opt b3lyp/6-31g(d,p)"          -> functional=b3lyp, basis=6-31g(d,p)
      "#p opt 6-31g(d,p) m062x"          -> functional=m062x, basis=6-31g(d,p)（基组在前）
    未能识别时整体作为计算模式，回填后关键词行仍与原 LOG 一致。
    """
    result = {'mode': '', 'functional': '', 'basis': '', 'route': route or ''}
    if not route:
        return result
    tokens = route.strip().split()
    slash_idx = next((i for i, t in enumerate(tokens)
                      if '/' in t and not t.startswith('%') and not t.startswith('(')), None)

    if slash_idx is None:
        # 没有 func/basis 形式：尝试找独立的基组与泛函 token（基组在前、泛函在后）
        basis_tok = next((t for t in tokens if _BASIS_RE.match(t)), '')
        func_tok = next((t for t in tokens if _FUNCTIONAL_RE.match(t)), '')
        if basis_tok and func_tok:
            skip = {basis_tok, func_tok}
            result['mode'] = ' '.join(t for t in tokens if t not in skip).strip()
            result['functional'] = func_tok
            result['basis'] = basis_tok
            return result
        result['mode'] = route.strip()
        return result

    func, _, basis = tokens[slash_idx].partition('/')
    result['mode'] = ' '.join(tokens[:slash_idx] + tokens[slash_idx + 1:]).strip()
    # 形如 "6-31g(d,p)/m062x"（基组在前）时交换，保证 field 名与实际含义一致
    if _BASIS_RE.match(func) and not _BASIS_RE.match(basis):
        func, basis = basis, func
    result['functional'] = func
    result['basis'] = basis
    return result


_TITLE_REJECT_RE = re.compile(
    r'^(%|#)'
    r'|[A-Za-z_]{2,}\s*='                       # ITRead= / NAtoms= / Charge= 等内部变量行
    r'|^[-+]?\d+([\s,.\-+]\d*)*$'               # 纯数字行
    r'|orientation\s*:'
    r'|Z-matrix|GradGrad|SCF Done|Entering |Termination|Berny'
    r'|Redundant|Frequencies|Isotropic|Kept|rms\s+Displacement'
    r'|Coordinates|^Center\b|Number\s+Number'
    r'|^-{3,}',
    re.IGNORECASE,
)


def looks_like_title(text: str) -> bool:
    """判断一行是否像 GJF 的标题行（排除 Gaussian 内部输出行，如 ITRead= ...）"""
    if not text:
        return False
    s = text.strip()
    if not s or len(s) > 200:
        return False
    if _TITLE_REJECT_RE.search(s):
        return False
    return True


def _extract_title(lines: list, route_idx: int) -> str:
    """标题行 = 输入回显区「电荷 自旋」行之前最近的一行合法文本。

    这种取法（而不是「关键词行之后第一行」）可以避开 Gaussian 打印的各种内部行，
    例如 ITRead= ... 之类，避免把它们误当成标题。
    """
    cm_idx = None
    for i in range(route_idx, min(route_idx + 400, len(lines))):
        if re.match(r'^\s*[-+]?\d+\s+[-+]?\d+\s*$', lines[i]):
            cm_idx = i
            break
    if cm_idx is None:
        return ''
    for j in range(cm_idx - 1, max(route_idx - 1, cm_idx - 15), -1):
        cand = lines[j].strip()
        if not cand:
            continue
        if _LOG_ROUTE_RE.match(lines[j]) or cand.startswith('%'):
            break                                     # 已回到关键词行 → 说明没有标题
        if looks_like_title(cand):
            return cand
    return ''


def _extract_charge_mult_from_echo(lines: list, route_idx: int):
    """从输入回显区读取「电荷 自旋」行（关键词行之后的第一处 "0 1" 形式）"""
    for i in range(route_idx, min(route_idx + 200, len(lines))):
        m = re.match(r'^\s*([-+]?\d+)\s+([-+]?\d+)\s*$', lines[i])
        if m:
            return int(m.group(1)), int(m.group(2))
    return None, None


def parse_log_text(text: str) -> dict:
    """解析 Gaussian LOG 文本，提取末帧几何 + 电荷/自旋 + 关键词行。

    返回 dict:
      ok           是否成功取到几何
      error        失败原因
      atomic_numbers / coords / atoms（含元素符号）
      natoms       原子数
      charge/mult  最后一帧对应的电荷与自旋多重度（可能为 None）
      route_first  首个关键词行（原始任务的关键词）
      route_last   最后一个关键词行（多 Link 任务时为最后一步）
      route_parts  split_route(route_first)
      title        标题行
      frames       坐标段总数
      frame_index  采用的坐标段序号（从 1 开始）
      source       坐标段类型（Standard/Input/Z-Matrix orientation）
      normal_termination / error_termination / link_count
    """
    from app.core.constants import ATOMIC_NUMBER_TO_SYMBOL

    lines = text.splitlines()
    blocks = _parse_orientation_blocks(lines)
    if not blocks:
        return {
            'ok': False,
            'error': '未找到坐标段（Standard orientation / Input orientation），该文件可能不是 Gaussian 输出',
            'natoms': 0,
        }

    rank = {'standard': 0, 'input': 1, 'z-matrix': 2}
    best = min(rank.get(b['kind'], 9) for b in blocks)
    same_kind = [b for b in blocks if rank.get(b['kind'], 9) == best]
    chosen = same_kind[-1]                       # 末帧 = 最后一段该类型坐标

    # 电荷/自旋：取最后一帧之前最后一次出现的 Charge/Multiplicity
    charge = mult = None
    for idx, line in enumerate(lines):
        m = _LOG_CHARGE_RE.search(line)
        if m and idx <= chosen['line']:
            charge, mult = int(m.group(1)), int(m.group(2))
    if charge is None:
        for line in lines:
            m = _LOG_CHARGE_RE.search(line)
            if m:
                charge, mult = int(m.group(1)), int(m.group(2))
                break

    route_lines = [i for i, ln in enumerate(lines) if _LOG_ROUTE_RE.match(ln)]
    route_first = lines[route_lines[0]].strip() if route_lines else ''
    route_last = lines[route_lines[-1]].strip() if route_lines else ''
    title = _extract_title(lines, route_lines[0]) if route_lines else ''

    # 回退：作业未正常结束时没有归档的 Charge/Multiplicity 行，
    # 此时从输入回显区「电荷 自旋」行读取（关键词行之后的第一处 "0 1"）
    if charge is None and route_lines:
        charge, mult = _extract_charge_mult_from_echo(lines, route_lines[0])

    atoms = []
    for an, (x, y, z) in zip(chosen['atomic_numbers'], chosen['coords']):
        atoms.append({
            'atomic_number': an,
            'symbol': ATOMIC_NUMBER_TO_SYMBOL.get(an, f'X{an}'),
            'x': x, 'y': y, 'z': z,
        })

    return {
        'ok': True,
        'error': '',
        'atomic_numbers': chosen['atomic_numbers'],
        'coords': chosen['coords'],
        'atoms': atoms,
        'natoms': len(atoms),
        'charge': charge,
        'mult': mult,
        'route_first': route_first,
        'route_last': route_last,
        'route_parts': split_route(route_first),
        'title': title,
        'frames': len(blocks),
        'frame_index': len(same_kind),
        'source': f"{chosen['kind'].capitalize()} orientation",
        'normal_termination': 'Normal termination of Gaussian' in text,
        'error_termination': 'Error termination' in text,
        'link_count': text.count('Entering Link 1'),
    }


def parse_log_file(log_path: str) -> dict:
    """读取 LOG 文件并解析（自动识别 .log/.out/.txt 等扩展名）"""
    if not os.path.exists(log_path):
        return {'ok': False, 'error': f'文件不存在: {log_path}', 'natoms': 0}
    try:
        return parse_log_text(_read_text(log_path))
    except Exception as e:                       # noqa: BLE001 - 解析失败要回传给前端
        return {'ok': False, 'error': f'解析失败: {e}', 'natoms': 0}


def parse_standard_orientation_at(lines: list, start: int):
    """解析标准坐标段"""
    for i in range(start, len(lines)):
        if 'Standard orientation:' in lines[i]:
            j = i + 5
            atomic_numbers = []
            coordinates = []
            while j < len(lines):
                line = lines[j].strip()
                if '----' in line or line == '':
                    break
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        num = int(parts[1])
                        x = float(parts[3])
                        y = float(parts[4])
                        z = float(parts[5])
                        atomic_numbers.append(num)
                        coordinates.append((x, y, z))
                    except ValueError:
                        break
                j += 1
            if atomic_numbers:
                return atomic_numbers, coordinates
    return None, None


def best_kind_blocks(lines: list) -> list:
    """所有坐标段中「最优类型」的那一批（Standard > Input > Z-Matrix），按出现顺序"""
    blocks = _parse_orientation_blocks(lines)
    if not blocks:
        return []
    rank = {'standard': 0, 'input': 1, 'z-matrix': 2}
    best = min(rank.get(b['kind'], 9) for b in blocks)
    return [b for b in blocks if rank.get(b['kind'], 9) == best]


def extract_modredundant_scan_steps(lines: list):
    """提取 ModRedundant 扫描步的构象

    真实 Gaussian 输出里，每个**优化步**都会打印一行
        Step number  1 out of a maximum of 409 on scan point   1 out of  18
    因此标记数远多于扫描点数；扫描点总数应取「out of M」里的 M。
    每个扫描点的输出顺序大致为：优化过程 → Optimization completed → 该点收敛构象 → 下一个点。
    主算法按扫描点编号变化为界取收敛构象；若点数仍不足（log 被截断等），
    退化为「每个扫描点取其区间内最后一段坐标」。
    """
    steps = []
    current_scan_point = None
    converged_point = None
    last_std_orient_atoms = None
    last_std_orient_coords = None
    converged_atoms = None
    converged_coords = None
    scan_point_pattern = re.compile(r'on scan point\s+(\d+)\s+out of\s+(\d+)')
    markers = []
    total_points = 0

    for i, line in enumerate(lines):
        m = scan_point_pattern.search(line)
        if m:
            point_no = int(m.group(1))
            total_points = max(total_points, int(m.group(2)))
            markers.append((i, point_no))
            if current_scan_point is not None and point_no != current_scan_point:
                if converged_atoms is not None:
                    steps.append((converged_point if converged_point is not None
                                  else current_scan_point, converged_atoms, converged_coords))
                converged_atoms = None
                converged_coords = None
                converged_point = None
                last_std_orient_atoms = None
                last_std_orient_coords = None
            current_scan_point = point_no

        if 'Standard orientation:' in line:
            atoms, coords = parse_standard_orientation_at(lines, i)
            if atoms is not None:
                last_std_orient_atoms = atoms
                last_std_orient_coords = coords

        if 'Optimization completed' in line and last_std_orient_atoms is not None:
            converged_atoms = last_std_orient_atoms
            converged_coords = last_std_orient_coords
            converged_point = current_scan_point

    if converged_atoms is not None:
        steps.append((converged_point if converged_point is not None else current_scan_point,
                      converged_atoms, converged_coords))

    expected = total_points or len(set(p for _i, p in markers))
    if not markers or len(steps) >= expected:
        return steps

    # 退化路径：每个扫描点取「该点区间内最后一段坐标」
    blocks = best_kind_blocks(lines)
    order = []
    for _i, p in markers:
        if p not in order:
            order.append(p)
    fallback = []
    for k, point in enumerate(order):
        start = next(i for i, p in markers if p == point)
        nxt = len(lines)
        if k + 1 < len(order):
            nxt = next((i for i, p in markers if p == order[k + 1]), len(lines))
        cands = [b for b in blocks if start <= b['line'] < nxt]
        if not cands:
            cands = [b for b in blocks if b['line'] < nxt]
        if not cands:
            continue
        block = max(cands, key=lambda b: b['line'])
        fallback.append((point, block['atomic_numbers'], block['coords']))
    return fallback if len(fallback) > len(steps) else steps


def parse_td_data(log_path: str) -> dict:
    """解析 TD 激发态信息"""
    orbital_data = parse_orbital_energies_advanced(log_path)
    orb_energy_map = {}
    for idx, eng in orbital_data.get('alpha_occ', []):
        orb_energy_map[idx] = eng
    for idx, eng in orbital_data.get('alpha_virt', []):
        orb_energy_map[idx] = eng
    for idx, eng in orbital_data.get('beta_occ', []):
        orb_energy_map[idx] = eng
    for idx, eng in orbital_data.get('beta_virt', []):
        orb_energy_map[idx] = eng

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    pattern = re.compile(r'Excited\s+State\s+1:')
    matches = list(pattern.finditer(content))
    if matches:
        last_match = matches[-1]
        content = content[last_match.start():]

    state_pattern = re.compile(
        r'^\s*Excited\s+State\s+(\d+):\s+(\S+)\s+([\d\.]+)\s+eV\s+([\d\.]+)\s+nm\s+f=([\d\.Ee+-]+)',
        re.M
    )
    trans_pattern = re.compile(r'^\s*(\d+)\s*->\s*(\d+)\s+([-+]?[\d\.Ee+-]+)')

    states = []
    blocks = re.split(r'\n(?=\s*Excited\s+State)', content)
    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue
        first_line = lines[0]
        m = state_pattern.match(first_line)
        if not m:
            continue
        state_num = int(m.group(1))
        mult_type = m.group(2)
        energy_eV = float(m.group(3))
        wavelength_nm = float(m.group(4))
        osc_strength = float(m.group(5))

        transitions = []
        for line in lines[1:]:
            t = trans_pattern.match(line)
            if t:
                from_orb = int(t.group(1))
                to_orb = int(t.group(2))
                coeff = float(t.group(3))
                percent = (coeff ** 2) * 100 * 2
                from_energy = orb_energy_map.get(from_orb, None)
                to_energy = orb_energy_map.get(to_orb, None)
                delta_energy = None
                if from_energy is not None and to_energy is not None:
                    delta_energy = to_energy - from_energy
                transitions.append({
                    'from': from_orb,
                    'to': to_orb,
                    'coeff': coeff,
                    'percent': percent,
                    'from_energy': from_energy,
                    'to_energy': to_energy,
                    'delta_energy': delta_energy,
                })
        states.append({
            'state_num': state_num,
            'mult_type': mult_type,
            'energy_eV': energy_eV,
            'wavelength_nm': wavelength_nm,
            'osc_strength': osc_strength,
            'transitions': transitions,
        })
    return {'orbital_map': orb_energy_map, 'states': states}


def parse_soc_ms_matrix(filename: str) -> dict:
    """从 ORCA 输出中提取 SOC 矩阵元"""
    with open(filename, 'r', encoding='utf-8') as f:
        text = f.read()

    pattern = r'(\d+)\s+(\d+)\s+\(\s*([-+]?\d+\.\d+)\s*,\s*([-+]?\d+\.\d+)\s*\)\s+\(\s*([-+]?\d+\.\d+)\s*,\s*([-+]?\d+\.\d+)\s*\)\s+\(\s*([-+]?\d+\.\d+)\s*,\s*([-+]?\d+\.\d+)\s*\)'
    matches = re.findall(pattern, text)
    data = {}
    for match in matches:
        t = int(match[0])
        s = int(match[1])
        vals = [float(x) for x in match[2:]]
        total = np.sqrt(sum(v ** 2 for v in vals))
        data[(t, s)] = total
    return data


def build_dataframe(data: dict, label: str = "") -> pd.DataFrame:
    """构建 SOC 矩阵 DataFrame"""
    if not data:
        return pd.DataFrame()
    t_indices = [t for t, _ in data.keys()]
    s_indices = [s for _, s in data.keys()]
    max_t = max(t_indices) if t_indices else 0
    max_s = max(s_indices) if s_indices else 0

    rows = []
    for t in range(1, max_t + 1):
        row = []
        for s in range(0, max_s + 1):
            row.append(data.get((t, s), 0.0))
        rows.append(row)

    df = pd.DataFrame(rows,
                      index=[f'T{i}' for i in range(1, max_t + 1)],
                      columns=[f'S{i}' for i in range(0, max_s + 1)])
    return df
