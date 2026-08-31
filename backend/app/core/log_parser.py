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


def parse_log_last_structure(filename: str):
    """从 LOG 文件提取最后的结构坐标"""
    try:
        with open(f"{filename}.log", 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None, None

    atomic_numbers = []
    coordinates = []
    re_std = re.compile(r'^\s*Standard\s+orientation\s*:', re.IGNORECASE)
    re_coord = re.compile(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)')
    in_std = False
    current_atomic = []
    current_coords = []

    for line in lines:
        if re_std.search(line):
            in_std = True
            current_atomic = []
            current_coords = []
            continue
        if in_std:
            if line.strip().startswith('---'):
                if current_atomic:
                    atomic_numbers = current_atomic
                    coordinates = current_coords
                    in_std = False
                continue
            m = re_coord.match(line)
            if m:
                an = int(m.group(2))
                x = float(m.group(4))
                y = float(m.group(5))
                z = float(m.group(6))
                current_atomic.append(an)
                current_coords.append((x, y, z))

    return atomic_numbers, coordinates


def extract_scan_header_info(lines: list):
    """提取扫描构象的头部信息"""
    route_lines = []
    title_lines = []
    charge = 0
    mult = 1
    for line in lines:
        if 'Charge =' in line and 'Multiplicity =' in line:
            m = re.search(r'Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(\d+)', line)
            if m:
                charge = int(m.group(1))
                mult = int(m.group(2))
                break
    if not route_lines:
        for line in lines:
            if line.strip().startswith('#'):
                route_lines.append(line.strip())
                break
    if not title_lines:
        for line in lines:
            s = line.strip()
            if s and not s.startswith('#') and not s.startswith('%'):
                if 'Entering' not in s and 'Link' not in s:
                    title_lines = [s]
                    break
    route_str = '\n'.join(route_lines) if route_lines else '#p b3lpy/6-31G(d,p)'
    title_str = ' '.join(title_lines) if title_lines else 'Scan Point'
    return route_str, title_str, charge, mult


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


def extract_modredundant_scan_steps(lines: list):
    """提取 ModRedundant 扫描步的构象"""
    steps = []
    current_scan_point = None
    last_std_orient_atoms = None
    last_std_orient_coords = None
    converged_atoms = None
    converged_coords = None
    scan_point_pattern = re.compile(r'on scan point\s+(\d+)\s+out of\s+\d+')

    for i, line in enumerate(lines):
        m = scan_point_pattern.search(line)
        if m:
            new_scan_point = int(m.group(1))
            if current_scan_point is not None and new_scan_point != current_scan_point:
                if converged_atoms is not None:
                    steps.append((current_scan_point, converged_atoms, converged_coords))
                converged_atoms = None
                converged_coords = None
                last_std_orient_atoms = None
                last_std_orient_coords = None
            current_scan_point = new_scan_point

        if 'Standard orientation:' in line:
            atoms, coords = parse_standard_orientation_at(lines, i)
            if atoms is not None:
                last_std_orient_atoms = atoms
                last_std_orient_coords = coords

        if 'Optimization completed' in line:
            if last_std_orient_atoms is not None:
                converged_atoms = last_std_orient_atoms
                converged_coords = last_std_orient_coords

    if current_scan_point is not None and converged_atoms is not None:
        steps.append((current_scan_point, converged_atoms, converged_coords))

    return steps


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
