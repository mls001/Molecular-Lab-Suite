import re
import os


def parse_fcclasses_output(file_path):
    """
    从 .out 文件提取频率和总重组能，从同目录的 HuangRhys.dat/txt 读取黄里斯因子
    返回:
        frequencies: list of float (cm⁻¹)   # 按模式顺序，与黄里斯因子一一对应
        huang_rhys: list of float (S_i)
        reorg_total: float (eV)
        reorg_contrib: list of float (eV)   # 分解重组能
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # ===== 1. 提取频率 =====
    frequencies = []

    # 方法1：查找 "FREQUENCIES (cm-1)" 部分
    freq_section = re.search(
        r'FREQUENCIES\s*\(cm-1\)\s*\n(.*?)(?=\n\s*\n\s*\n|\n\s*={2,}|Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if freq_section:
        section_text = freq_section.group(1)
        # 按行拆分，每行可能包含多个 "序号 数值" 对
        for line in section_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 匹配一行中的多个 "序号 数值" 对
            # 例如: "  1   9.93298   2   11.84996"
            pairs = re.findall(r'(\d+)\s+([\d\.Ee+-]+)', line)
            for idx_str, val_str in pairs:
                freq = float(val_str)
                if freq > 0:
                    frequencies.append(freq)

    # 方法2：如果方法1失败，尝试逐行扫描
    if not frequencies:
        lines = content.split('\n')
        in_freq = False
        for line in lines:
            if re.search(r'FREQUENCIES\s*\(cm-1\)', line, re.IGNORECASE):
                in_freq = True
                continue
            if in_freq:
                # 遇到空行或分隔线，结束
                if not line.strip() or re.search(r'={2,}|-{2,}', line):
                    break
                # 匹配一行中的多个 "序号 数值"
                pairs = re.findall(r'(\d+)\s+([\d\.Ee+-]+)', line.strip())
                for idx_str, val_str in pairs:
                    freq = float(val_str)
                    if freq > 0:
                        frequencies.append(freq)

    # ===== 2. 读取黄里斯因子（外部文件） =====
    dir_name = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    hr_file_candidates = [
        os.path.join(dir_name, f"{base_name}_HuangRhys.dat"),
        os.path.join(dir_name, f"{base_name}_HuangRhys.txt"),
        os.path.join(dir_name, f"{base_name}.HuangRhys.dat"),
        os.path.join(dir_name, f"{base_name}.HuangRhys.txt"),
        os.path.join(dir_name, "HuangRhys.dat"),
        os.path.join(dir_name, "HuangRhys.txt"),
        os.path.join(dir_name, "HuangRhys"),
    ]

    hr_content = None
    for cand in hr_file_candidates:
        if os.path.exists(cand):
            with open(cand, 'r', encoding='utf-8', errors='ignore') as f:
                hr_content = f.read()
            break

    huang_rhys = []
    if hr_content:
        for line in hr_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^\s*(\d+)\s+([\d\.Ee+-]+)\s*$', line)
            if match:
                hr_value = float(match.group(2))
                if hr_value >= 0:
                    huang_rhys.append(hr_value)

    # ===== 3. 对齐频率和黄里斯因子 =====
    if huang_rhys and frequencies:
        # 以较短的为准
        n = min(len(huang_rhys), len(frequencies))
        huang_rhys = huang_rhys[:n]
        frequencies = frequencies[:n]
    elif huang_rhys and not frequencies:
        frequencies = [0.0] * len(huang_rhys)
    elif frequencies and not huang_rhys:
        huang_rhys = [0.0] * len(frequencies)

    # ===== 4. 提取总重组能（eV）=====
    reorg_total = 0.0

    # 先尝试精确匹配：REORGANIZATION ENERGY 后面跟着 (Hartree) 和 (eV)
    # 不依赖换行，使用 DOTALL 跨行匹配
    patterns = [
        # 匹配 "REORGANIZATION ENERGY" 后任意内容，然后数字 (Hartree)，再数字 (eV)
        r'REORGANIZATION\s+ENERGY.*?([\d\.]+)\s*\(Hartree\).*?([\d\.]+)\s*\(eV\)',
        # 匹配 "REORGANIZATION ENERGY" 后直接跟数字 (eV)
        r'REORGANIZATION\s+ENERGY.*?([\d\.]+)\s*\(eV\)',
        # 匹配 "REORGANIZATION ENERGY" 后跟数字 eV（无括号）
        r'REORGANIZATION\s+ENERGY.*?([\d\.]+)\s*eV',
        # 更宽松的匹配
        r'REORGANIZATION ENERGY[\s\S]*?([\d\.]+)\s*\(eV\)',
    ]

    for pattern in patterns:
        m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if m:
            # 如果匹配到两个值，取第二个（eV），否则取第一个
            if len(m.groups()) >= 2:
                reorg_total = float(m.group(2))
            else:
                reorg_total = float(m.group(1))
            break

    # 如果仍然为0，尝试查找 "0.013869  (Hartree)" 模式
    if reorg_total == 0.0:
        m = re.search(r'([\d\.]+)\s*\(Hartree\)\s*\n\s*([\d\.]+)\s*\(eV\)', content)
        if m:
            reorg_total = float(m.group(2))

    # ===== 5. 计算分解重组能 =====
    reorg_contrib = []
    if huang_rhys and frequencies:
        n = min(len(huang_rhys), len(frequencies))
        for i in range(n):
            # eV = S * ω * (27.211386 / 219474.63137)
            # 如果频率为0，贡献为0
            if frequencies[i] > 0:
                reorg_ev = huang_rhys[i] * frequencies[i] * 27.211386 / 219474.63137
            else:
                reorg_ev = 0.0
            reorg_contrib.append(reorg_ev)

    return {
        'frequencies': frequencies,
        'huang_rhys': huang_rhys,
        'reorg_total': reorg_total,
        'reorg_contrib': reorg_contrib,
    }