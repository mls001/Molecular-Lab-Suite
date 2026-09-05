import os
import re


def modify_gjf_content(input_path: str, mem: str, nprocshared: str, keyword: str,
                       charge: str, mult: str, chk_name: str = None) -> list:
    """修改 GJF 文件内容，返回新内容行列表"""
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if chk_name is None:
        chk_filename = f"{os.path.basename(input_path).replace('.gjf', '.chk')}"
    else:
        chk_filename = os.path.basename(chk_name)

    new_lines = []
    chk_replaced = False
    mem_replaced = False
    nproc_replaced = False
    keyword_replaced = False
    charge_mult_replaced = False
    title_found = False
    i = 0

    while i < len(lines):
        line = lines[i]
        if re.match(r'^%chk\s*=', line, re.IGNORECASE):
            new_lines.append(f"%chk={chk_filename}\n")
            chk_replaced = True
            i += 1
            continue
        elif re.match(r'^%mem\s*=', line, re.IGNORECASE):
            new_lines.append(f"%mem={mem}\n")
            mem_replaced = True
            i += 1
            continue
        elif re.match(r'^%nproc(shared)?\s*=', line, re.IGNORECASE):
            new_lines.append(f"%nprocshared={nprocshared}\n")
            nproc_replaced = True
            i += 1
            continue
        elif re.match(r'^\s*#', line) and not keyword_replaced:
            new_lines.append(f"{keyword}\n")
            keyword_replaced = True
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (nxt.strip().startswith('#') or nxt[0] == ' '):
                    i += 1
                else:
                    break
            continue
        elif title_found and not charge_mult_replaced and re.match(r'^\s*[-+]?\d+\s+[-+]?\d+\s*$', line):
            new_lines.append(f"{charge} {mult}\n")
            charge_mult_replaced = True
            i += 1
            continue
        elif not title_found and not re.match(r'^\s*%', line) and not re.match(r'^\s*#', line) and line.strip():
            new_lines.append(line)
            title_found = True
            i += 1
            continue
        else:
            new_lines.append(line)
            i += 1

    # 补全缺失行
    if not chk_replaced:
        new_lines.insert(0, f"%chk={chk_filename}\n")
    if not mem_replaced:
        insert_pos = 1 if chk_replaced else 0
        new_lines.insert(insert_pos, f"%mem={mem}\n")
    if not nproc_replaced:
        insert_pos = 0
        if not chk_replaced:
            insert_pos += 1
        if not mem_replaced:
            insert_pos += 1
        new_lines.insert(insert_pos, f"%nprocshared={nprocshared}\n")
    if not keyword_replaced:
        insert_idx = 0
        for idx, ln in enumerate(new_lines):
            if not ln.startswith('%'):
                insert_idx = idx
                break
        else:
            insert_idx = len(new_lines)
        new_lines.insert(insert_idx, f"{keyword}\n")

    return new_lines


def build_gjf_text(mem: str, nprocshared: str, keyword: str, charge, mult,
                   atomic_numbers: list, coordinates: list,
                   title: str = "Generated from log", chk_name: str = None,
                   symbols: list = None) -> str:
    """根据坐标生成完整的 GJF 文本（LOG → GJF 用）

    chk_name 为 None 时由调用方决定；symbols 可直接给元素符号，否则由原子序数查表。
    """
    from app.core.constants import ATOMIC_NUMBER_TO_SYMBOL

    if symbols is None:
        symbols = [ATOMIC_NUMBER_TO_SYMBOL.get(int(an), f"X{an}") for an in atomic_numbers]

    lines = []
    if chk_name:
        lines.append(f"%chk={chk_name}\n")
    lines.append(f"%mem={mem}\n")
    lines.append(f"%nprocshared={nprocshared}\n")
    lines.append(f"{keyword}\n")
    lines.append("\n")
    lines.append(f"{title}\n")
    lines.append("\n")
    lines.append(f"{charge} {mult}\n")
    for sym, coord in zip(symbols, coordinates):
        x, y, z = coord
        lines.append(f" {sym:<2s}  {x:12.6f} {y:12.6f} {z:12.6f}\n")
    lines.append("\n")
    return ''.join(lines)


def write_gjf_from_coords(output_path: str, mem: str, nprocshared: str, keyword: str,
                          charge: str, mult: str, atomic_numbers: list, coordinates: list,
                          title: str = "Generated from log"):
    """从坐标写入 GJF 文件（保留旧接口）"""
    text = build_gjf_text(
        mem=mem, nprocshared=nprocshared, keyword=keyword, charge=charge, mult=mult,
        atomic_numbers=atomic_numbers, coordinates=coordinates, title=title,
        chk_name=os.path.basename(output_path).replace('.gjf', '.chk'),
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text

