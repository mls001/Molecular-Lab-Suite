"""生成 Gaussian / ORCA 输入文件（对标 example/input 里的既有写法）"""

# Gaussian 计算模式预设（沿用「修改GJF」页面的习惯）
GAUSSIAN_MODES = [
    '#p opt',
    '#p opt freq',
    '#p freq',
    '#p td=(50-50,nstates=10)',
    '#p td opt',
    '#p td opt freq',
    '#p sp',
]

# ORCA 预设：keywords 拼进 `!` 行，blocks 为额外 %block
ORCA_PRESETS = [
    {
        'id': 'soc_tddft',
        'label': 'SOC-TDDFT（含 dosoc，发光/自旋轨道耦合）',
        'keywords': 'miniprint tightSCF',
        'blocks': [('%tddft', ['nroots {nstates}', 'dosoc true', 'tda false', 'printlevel 3'])],
    },
    {
        'id': 'tddft',
        'label': 'TD-DFT（激发态）',
        'keywords': 'miniprint tightSCF',
        'blocks': [('%tddft', ['nroots {nstates}', 'tda false', 'printlevel 3'])],
    },
    {
        'id': 'opt_freq',
        'label': 'Opt + Freq（几何优化 + 频率）',
        'keywords': 'Opt Freq tightSCF',
        'blocks': [],
    },
    {
        'id': 'opt',
        'label': 'Opt（几何优化）',
        'keywords': 'Opt tightSCF',
        'blocks': [],
    },
    {
        'id': 'opt_ts',
        'label': 'OptTS + Freq（过渡态）',
        'keywords': 'OptTS Freq tightSCF',
        'blocks': [],
    },
    {
        'id': 'freq',
        'label': 'Freq（频率/重组能）',
        'keywords': 'Freq tightSCF',
        'blocks': [],
    },
    {
        'id': 'sp',
        'label': 'Single Point（单点能）',
        'keywords': 'tightSCF',
        'blocks': [],
    },
]

ORCA_BASIS_PRESETS = ['6-31G(d,p)', '6-311G(d,p)', 'def2-SVP', 'def2-TZVP', 'def2-TZVPP',]
ORCA_FUNC_PRESETS = ['m062x', 'b3lyp', 'b3lyp/G', 'wb97x-d3', 'pbe0', 'cam-b3lyp']

GAUSSIAN_BASIS_PRESETS = ['6-31g(d,p)', '6-31g(d)', '6-311g(d,p)', '6-311+g(d,p)',
                          'def2svp', 'def2tzvp', 'def2tzvpp', 'cc-pvdz']
GAUSSIAN_FUNC_PRESETS = ['b3lyp', 'm062x', 'wb97xd', 'cam-b3lyp', 'pbe1pbe']


def _coords_block(atoms, symbol_width=2, coord_width=16, decimals=8):
    lines = []
    for sym, x, y, z in atoms:
        lines.append(f' {sym:<{symbol_width}s} {x:>{coord_width}.{decimals}f} '
                     f'{y:>{coord_width}.{decimals}f} {z:>{coord_width}.{decimals}f}')
    return '\n'.join(lines)


def build_gaussian(atoms, charge=0, mult=1, functional='m062x', basis='6-31g(d,p)',
                   calc='#p opt', mem='20GB', nproc='8', chk_name='', title='',
                   extra_keywords='') -> str:
    """Gaussian 输入（.gjf）：
        %mem / %nproc / %chk → 关键词行 → 空行 → 标题 → 空行 → 电荷 自旋 → 坐标
    """
    parts = []
    if mem:
        parts.append(f'%mem={mem}')
    if nproc:
        parts.append(f'%nproc={nproc}')
    if chk_name:
        parts.append(f'%chk={chk_name}')

    route = (calc or '').strip()
    if not route.startswith('#'):
        route = '#p ' + route
    fb = ' '.join([t for t in [functional, basis] if t])
    extra = (extra_keywords or '').strip()
    route = ' '.join([t for t in [route, fb, extra] if t])

    header = '\n'.join(parts)
    return (f'{header}\n{route}\n\n'
            f'{title or "Title Card Required"}\n\n'
            f'{int(charge)} {int(mult)}\n'
            f'{_coords_block(atoms)}\n\n')


def build_orca(atoms, charge=0, mult=1, functional='m062x', basis='def2-SVP',
               preset='soc_tddft', nstates=10, maxcore=2500, nprocs=4,
               title='', extra_keywords='', extra_blocks='') -> str:
    """ORCA 输入（.inp）：! 关键词 → %maxcore → %block → *xyz 电荷 多重度 → 坐标 → *"""
    preset_def = next((p for p in ORCA_PRESETS if p['id'] == preset), ORCA_PRESETS[0])
    keywords = ' '.join([t for t in [functional, basis, preset_def['keywords']] if t])
    if nprocs and int(nprocs) > 1:
        keywords += f' pal{int(nprocs)}'
    extra = (extra_keywords or '').strip()
    if extra:
        keywords += ' ' + extra

    lines = [f'! {keywords}']
    if title:
        lines.append(f'# {title}')
    if maxcore:
        lines.append(f'%maxcore {int(maxcore)}')

    for name, body in preset_def['blocks']:
        lines.append(name)
        for row in body:
            lines.append(row.replace('{nstates}', str(int(nstates))))
        lines.append('end')

    blk = (extra_blocks or '').strip()
    if blk:
        lines.append(blk)

    lines.append(f'*xyz {int(charge)} {int(mult)}')
    lines.append(_coords_block(atoms, coord_width=20))
    lines.append('*')
    return '\n'.join(lines) + '\n'
