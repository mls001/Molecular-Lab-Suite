"""分子结构读写 / 转换 / 编辑（基于 RDKit）

支持格式：
    .mls  —— 本软件自有格式，每行一个原子：元素 x y z
    .mol / .sdf / .pdb / .xyz / .smi      —— RDKit 原生读取
    .gjf / .com / .inp / .log / .out      —— 从文本里提取坐标（Gaussian / ORCA / 通用）

主要能力：
    read_molecule()   任意格式 → RDKit Mol（有坐标则直接建键，只有 2D/无坐标则按需生成 3D）
    mol_to_dict()     Mol → 前端用的原子/键/信息 + 2D SVG（含隐式氢数，供 2D 绘制标注）
    layout_2d()       生成理想 2D 坐标（对标 ChemDraw 的 Clean Up Structure）
    ensure_3d()       ETKDG 嵌入 + 力场优化，得到"合理结构"
    apply_edit()      增删原子/键、改元素/电荷、改键级、加环模板、加氢去氢、改坐标
    save_mls()        按 "元素 x y z" 写出 .mls 到 Mols 目录
"""
import math
import os
import re

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors
from rdkit.Geometry import Point3D

from app.core.constants import SYMBOL_TO_ATOMIC_NUMBER

SUPPORTED_EXT = ['.mls', '.mol', '.sdf', '.xyz', '.pdb', '.smi',
                 '.gjf', '.com', '.inp', '.log', '.out']

_ATOM_LINE_RE = re.compile(
    r'^\s*([A-Z][a-z]?|[a-z]{1,2})\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$'
)
_GAUSS_CM_RE = re.compile(r'^\s*(-?\d+)\s+(\d+)\s*$')
_ORCA_XYZ_RE = re.compile(r'^\s*\*xyz\s+(-?\d+)\s+(\d+)\s*$', re.I)

# ============ 环模板（对标 ChemDraw 的 Ring tools） ============
# key → (SMILES, 中文名)
RING_TEMPLATES = [
    ('benzene', 'c1ccccc1', '苯环'),
    ('cyclohexane', 'C1CCCCC1', '环己烷'),
    ('cyclopentane', 'C1CCCC1', '环戊烷'),
    ('cyclobutane', 'C1CCC1', '环丁烷'),
    ('cyclopropane', 'C1CC1', '环丙烷'),
    ('cycloheptane', 'C1CCCCCC1', '环庚烷'),
    ('cyclooctane', 'C1CCCCCCC1', '环辛烷'),
    ('naphthalene', 'c1ccc2ccccc2c1', '萘'),
    ('pyridine', 'c1ccncc1', '吡啶'),
    ('pyrimidine', 'c1cncnc1', '嘧啶'),
    ('furan', 'c1ccoc1', '呋喃'),
    ('pyrrole', 'c1cc[nH]c1', '吡咯'),
    ('thiophene', 'c1ccsc1', '噻吩'),
    ('imidazole', 'c1cnc[nH]1', '咪唑'),
    ('indole', 'c1ccc2[nH]ccc2c1', '吲哚'),
]
RING_SMILES = {k: s for k, s, _label in RING_TEMPLATES}
RING_LABELS = {k: label for k, _s, label in RING_TEMPLATES}

_BOND_LEN = 1.4                                   # 绘制用标准键长（Å）


# ============ Mols 目录（本软件自有分子文件） ============

def mols_dir() -> str:
    """.mls 保存目录：打包后位于 .exe 同级的 Mols（由主进程通过 MLS_MOLS_DIR 告知）"""
    d = os.environ.get('MLS_MOLS_DIR')
    if not d:
        root = os.environ.get('MLS_PROJECT_ROOT') or os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        d = os.path.join(root, 'Mols')
    os.makedirs(d, exist_ok=True)
    return d


def _symbol(z: int) -> str:
    return Chem.GetPeriodicTable().GetElementSymbol(int(z))


# ============ .mls 读写 ============

def parse_mls_text(text: str):
    """解析 .mls：每行 `元素 x y z`（# 开头为注释）"""
    atoms = []
    for raw in (text or '').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith('!'):
            continue
        m = _ATOM_LINE_RE.match(line)
        if m:
            sym = m.group(1).capitalize()
            atoms.append((sym, float(m.group(2)), float(m.group(3)), float(m.group(4))))
    return atoms


def format_mls(atoms) -> str:
    """写出 .mls 文本：每行 `元素 x y z`"""
    lines = [f'{sym:<2s} {x:16.8f} {y:16.8f} {z:16.8f}' for sym, x, y, z in atoms]
    return '\n'.join(lines) + ('\n' if lines else '')


def save_mls(name: str, atoms, directory: str = None) -> str:
    """保存为 Mols/<name>.mls，返回完整路径"""
    safe = re.sub(r'[\\/:*?"<>|]+', '_', (name or '').strip()) or 'molecule'
    if not safe.lower().endswith('.mls'):
        safe += '.mls'
    folder = directory or mols_dir()
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, safe)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(format_mls(atoms))
    return path


def list_mls(directory: str = None):
    folder = directory or mols_dir()
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith('.mls'):
            full = os.path.join(folder, name)
            out.append({'name': name, 'path': full, 'size': os.path.getsize(full)})
    return out


# ============ 文本坐标提取（gjf / orca in / log / out / xyz） ============

def atoms_from_text(text: str):
    """从任意化学文本里提取最后一组坐标，返回 (atoms, charge, mult)"""
    lines = (text or '').splitlines()
    charge = mult = None

    # ORCA 输入里的 *xyz c m
    for i, ln in enumerate(lines):
        m = _ORCA_XYZ_RE.match(ln)
        if m:
            charge, mult = int(m.group(1)), int(m.group(2))
            atoms = []
            for nxt in lines[i + 1:]:
                if nxt.strip().startswith('*'):
                    break
                am = _ATOM_LINE_RE.match(nxt)
                if am:
                    atoms.append((am.group(1).capitalize(), float(am.group(2)),
                                  float(am.group(3)), float(am.group(4))))
            if len(atoms) >= 1:
                return atoms, charge, mult

    # Gaussian 的 Standard/Input orientation
    try:
        from app.core.log_parser import parse_log_file
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text or '')
            tmp = f.name
        info = parse_log_file(tmp)
        os.unlink(tmp)
        if info.get('ok') and info.get('atomic_numbers'):
            atoms = [(_symbol(z), c[0], c[1], c[2])
                     for z, c in zip(info['atomic_numbers'], info['coords'])]
            return atoms, info.get('charge'), info.get('mult')
    except Exception:
        pass

    # 通用回退：连续 ≥2 行 "元素 x y z"，取最后一组
    runs, cur = [], []
    for ln in lines:
        m = _ATOM_LINE_RE.match(ln)
        if m:
            cur.append((m.group(1).capitalize(), float(m.group(2)),
                        float(m.group(3)), float(m.group(4))))
        else:
            if len(cur) >= 2:
                runs.append(cur)
            cur = []
    if len(cur) >= 2:
        runs.append(cur)
    if runs:
        return runs[-1], charge, mult

    # 最后再试电荷/多重度行
    for ln in lines:
        m = _GAUSS_CM_RE.match(ln)
        if m and charge is None:
            charge, mult = int(m.group(1)), int(m.group(2))
            break
    return [], charge, mult


def _read_text(path: str) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'latin-1'):
        try:
            with open(path, 'r', encoding=enc, errors='ignore') as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


# ============ Mol 构建 ============

def xyz_block(atoms, comment='mls') -> str:
    body = '\n'.join(f'{sym:<2s} {x:16.8f} {y:16.8f} {z:16.8f}' for sym, x, y, z in atoms)
    return f'{len(atoms)}\n{comment}\n{body}\n'


def mol_from_atoms(atoms, charge: int = 0):
    """原子坐标 → Mol（用 RDKit DetermineBonds 推断键级；失败则退化为无键）"""
    if not atoms:
        raise ValueError('没有原子')
    mol = Chem.MolFromXYZBlock(xyz_block(atoms))
    if mol is None:
        raise ValueError('坐标无法解析为分子')
    warning = ''
    try:
        from rdkit.Chem import rdDetermineBonds
        rdDetermineBonds.DetermineBonds(mol, charge=int(charge or 0))
        Chem.SanitizeMol(mol)
    except Exception as e:                       # noqa: BLE001 - 无键也能显示/编辑
        warning = f'未能自动判断键级（{e}）；已按无键结构载入，可在右侧手动建键'
        mol = Chem.RWMol(mol)
        for atom in mol.GetAtoms():
            atom.SetNoImplicit(True)
        mol = mol.GetMol()
    return mol, warning


def read_molecule(path: str = None, content: str = None, ext: str = None, charge: int = 0):
    """读取任意支持的分子文件 → (mol, warning, meta)"""
    warning = ''
    meta = {'charge': charge, 'mult': 1}

    if content is None:
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f'文件不存在: {path}')
        content = _read_text(path)
    name = os.path.basename(path) if path else 'molecule'
    e = (ext or os.path.splitext(name)[1] or '').lower()

    mol = None
    if e == '.mls':
        atoms = parse_mls_text(content)
        if not atoms:
            raise ValueError('该 .mls 文件里没有可识别的坐标行（应为“元素 x y z”）')
        mol, warning = mol_from_atoms(atoms, charge)
    elif e in ('.mol', '.sdf'):
        mol = Chem.MolFromMolBlock(content, removeHs=False, sanitize=True)
        if mol is None:
            mol = Chem.MolFromMolBlock(content, removeHs=False, sanitize=False)
            if mol is not None:
                warning = '分子未通过 RDKit 净化（可能是价键异常），部分编辑功能可能受限'
    elif e == '.xyz':
        atoms, c, m = atoms_from_text(content)
        if not atoms:
            raise ValueError('该 .xyz 文件里没有可识别的坐标行')
        meta['charge'], meta['mult'] = (c if c is not None else charge), (m or 1)
        mol, warning = mol_from_atoms(atoms, meta['charge'])
    elif e == '.pdb':
        mol = Chem.MolFromPDBBlock(content, removeHs=False)
    elif e == '.smi':
        mol = Chem.MolFromSmiles(content.strip().split()[0] if content.strip() else '')
    else:                                        # .gjf .com .inp .log .out 等文本
        atoms, c, m = atoms_from_text(content)
        if not atoms:
            raise ValueError('该文件里没有找到原子坐标（支持 .mls/.mol/.xyz/.pdb/.smi/.gjf/.inp/.log/.out）')
        meta['charge'], meta['mult'] = (c if c is not None else charge), (m or 1)
        mol, warning = mol_from_atoms(atoms, meta['charge'])

    if mol is None:
        raise ValueError(f'无法读取分子（{e or "未知格式"}）')
    return mol, warning, meta


# ============ 3D / 2D 处理 ============

def has_3d(mol) -> bool:
    if mol is None or mol.GetNumConformers() == 0:
        return False
    conf = mol.GetConformer()
    if not conf.Is3D():
        return False
    positions = conf.GetPositions()
    return any(abs(p[2]) > 1e-3 for p in positions) or mol.GetNumAtoms() <= 2


def stereo_from_2d(mol):
    """把 2D 画法里的顺反（E/Z）几何转成分子立体标记

    molblock 本身不携带双键顺反信息（只靠坐标体现），重新读入后必须由坐标重新感知，
    否则 ETKDG 会自己随便选一侧，导致 3D 与 2D 画的不一致（例如画了反式却生成顺式）。
    """
    if mol is None or mol.GetNumAtoms() == 0 or mol.GetNumConformers() == 0:
        return mol
    if has_3d(mol):
        return mol
    m = Chem.Mol(mol)
    try:
        Chem.AssignStereochemistry(m, cleanIt=True, force=True)
        Chem.DetectBondStereochemistry(m, confId=0)
        Chem.AssignStereochemistry(m, cleanIt=True, force=True)
    except Exception:                             # noqa: BLE001 - 感知失败就按原样处理
        return mol
    return m


def _dihedral_deg(conf, i: int, j: int, k: int, l: int) -> float:
    p = [conf.GetAtomPosition(x) for x in (i, j, k, l)]
    v = lambda a, b: (b.x - a.x, b.y - a.y, b.z - a.z)          # noqa: E731
    cr = lambda u, w: (u[1] * w[2] - u[2] * w[1],               # noqa: E731
                       u[2] * w[0] - u[0] * w[2],
                       u[0] * w[1] - u[1] * w[0])
    dt = lambda u, w: u[0] * w[0] + u[1] * w[1] + u[2] * w[2]   # noqa: E731
    b1, b2, b3 = v(p[0], p[1]), v(p[1], p[2]), v(p[2], p[3])
    n1, n2 = cr(b1, b2), cr(b2, b3)
    L = math.sqrt(dt(b2, b2)) or 1.0
    m = cr(n1, (b2[0] / L, b2[1] / L, b2[2] / L))
    return math.degrees(math.atan2(dt(m, n2), dt(n1, n2)))


def _double_bond_refs(mol):
    """每个「有取代基的双键」→ (i, j, ni, nj)：两侧各取一个参照取代原子（优先重原子、序号最小）"""
    out = []
    for b in mol.GetBonds():
        if abs(b.GetBondTypeAsDouble() - 2.0) > 0.01:
            continue
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        picks = []
        for a, other in ((mol.GetAtomWithIdx(i), j), (mol.GetAtomWithIdx(j), i)):
            nbrs = [n.GetIdx() for n in a.GetNeighbors() if n.GetIdx() != other]
            heavy = [n for n in nbrs if mol.GetAtomWithIdx(n).GetAtomicNum() > 1]
            pool = heavy or nbrs
            if not pool:
                picks = []
                break
            picks.append(min(pool))
        if len(picks) == 2:
            out.append((i, j, picks[0], picks[1]))
    return out


def _subtree(mol, start: int, blocked: int):
    """从 start 出发、不经过 blocked 能到达的原子集合（双键一侧的取代基）"""
    seen = {start}
    stack = [start]
    while stack:
        k = stack.pop()
        for n in mol.GetAtomWithIdx(k).GetNeighbors():
            t = n.GetIdx()
            if t == blocked or t in seen:
                continue
            seen.add(t)
            stack.append(t)
    return seen


def enforce_stereo(mol3d, ref2d):
    """把 2D 画法里的顺反强制施加到 3D 上

    做法：对每个有取代基的双键比较 2D/3D 的参照二面角，如果顺反相反，就把一侧取代基
    绕双键轴整体转 180°（键长键角完全不变，只改这条双键的扭转），从而保证 3D 与画的一致。
    返回 (新 mol, 修正条数)。
    """
    if mol3d is None or ref2d is None:
        return mol3d, 0
    if mol3d.GetNumConformers() == 0 or ref2d.GetNumConformers() == 0:
        return mol3d, 0
    n = mol3d.GetNumAtoms()
    refs = [r for r in _double_bond_refs(ref2d) if max(r) < n]
    if not refs:
        return mol3d, 0
    m = Chem.Mol(mol3d)
    conf = m.GetConformer()
    conf2 = ref2d.GetConformer()
    fixed = 0
    for (i, j, ni, nj) in refs:
        try:
            d2 = _dihedral_deg(conf2, ni, i, j, nj)
            d3 = _dihedral_deg(conf, ni, i, j, nj)
        except Exception:                         # noqa: BLE001
            continue
        if 70 < abs(d2) < 110:                    # 2D 上就模糊，不做判断
            continue
        if (abs(d2) < 90) == (abs(d3) < 90):      # 顺反一致
            continue
        # 把 j 侧子树绕 i–j 轴转 180°
        p1, p2 = conf.GetAtomPosition(i), conf.GetAtomPosition(j)
        ax = (p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
        L = math.sqrt(ax[0] ** 2 + ax[1] ** 2 + ax[2] ** 2)
        if L < 1e-6:
            continue
        u = (ax[0] / L, ax[1] / L, ax[2] / L)
        for k in _subtree(m, j, i):
            q = conf.GetAtomPosition(k)
            w = (q.x - p1.x, q.y - p1.y, q.z - p1.z)
            dot = w[0] * u[0] + w[1] * u[1] + w[2] * u[2]
            perp = (w[0] - dot * u[0], w[1] - dot * u[1], w[2] - dot * u[2])
            conf.SetAtomPosition(k, Point3D(p1.x - perp[0] + dot * u[0],
                                            p1.y - perp[1] + dot * u[1],
                                            p1.z - perp[2] + dot * u[2]))
        fixed += 1
    return (m if fixed else mol3d), fixed


def ensure_3d(mol, ff: str = 'MMFF94', max_iters: int = 800, optimize: bool = True):
    """保证有合理的 3D 结构：无 3D 时用 ETKDG 嵌入，再做力场优化

    optimize=False 时只做 ETKDG 嵌入（快，供绘制时实时同步大分子用）
    """
    note = ''
    mol = Chem.Mol(mol)
    ref2d = None
    if mol.GetNumConformers() and not has_3d(mol):
        ref2d = Chem.Mol(mol)                     # 记住 2D 画法，用于最后核对/修正顺反
    mol = stereo_from_2d(mol)                     # 2D 画法里的顺反要带进 3D
    if not optimize:
        params = AllChem.ETKDGv3()
        params.randomSeed = 0xf00d
        params.useRandomCoords = True
        if AllChem.EmbedMolecule(mol, params) != 0:
            return mol, '3D 嵌入失败（可能缺少氢或价键异常），已保留原坐标'
        mol, fixed = enforce_stereo(mol, ref2d)
        if fixed:
            note = f'已按 2D 画法修正 {fixed} 处双键顺反'
        return mol, '已用 ETKDG 生成 3D 构象（未做力场优化）' + (('；' + note) if note else '')
    if mol.GetNumConformers() == 0 or not has_3d(mol):
        params = AllChem.ETKDGv3()
        params.randomSeed = 0xf00d
        params.useRandomCoords = True
        if AllChem.EmbedMolecule(mol, params) != 0:
            note = '3D 嵌入失败（可能缺少氢或价键异常），已保留原坐标'
            return mol, note
        note = '已用 ETKDG 生成 3D 构象'
    try:
        if ff.upper() == 'UFF':
            AllChem.UFFOptimizeMolecule(mol, maxIters=max_iters)
            note = (note + '；' if note else '') + 'UFF 优化完成'
        elif AllChem.MMFFHasAllMoleculeParams(mol):
            AllChem.MMFFOptimizeMolecule(mol, maxIters=max_iters)
            note = (note + '；' if note else '') + 'MMFF94 优化完成'
        else:
            AllChem.UFFOptimizeMolecule(mol, maxIters=max_iters)
            note = (note + '；' if note else '') + '缺少 MMFF 参数，改用 UFF 优化'
    except Exception as e:                       # noqa: BLE001
        note = (note + '；' if note else '') + f'力场优化跳过（{e}）'
    mol, fixed = enforce_stereo(mol, ref2d)      # 最终核对：3D 的顺反必须与 2D 画法一致
    if fixed:
        note = (note + '；' if note else '') + f'已按 2D 画法修正 {fixed} 处双键顺反'
    return mol, note


def layout_2d(mol):
    """生成理想 2D 坐标（ChemDraw 的 Clean Up Structure）：z 归零 + 标记为 2D 构象"""
    m = Chem.Mol(mol)
    try:
        AllChem.Compute2DCoords(m)
    except Exception:                             # noqa: BLE001 - 已有多边形/坐标时也可继续
        pass
    if m.GetNumConformers() == 0:
        m.AddConformer(Chem.Conformer(m.GetNumAtoms()), assignId=True)
    conf = m.GetConformer()
    for i in range(m.GetNumAtoms()):
        p = conf.GetAtomPosition(i)
        conf.SetAtomPosition(i, Point3D(p.x, p.y, 0.0))
    conf.Set3D(False)
    return m


def _mean_bond_length(mol) -> float:
    conf = mol.GetConformer() if mol.GetNumConformers() else None
    if conf is None:
        return _BOND_LEN
    lens = []
    for b in mol.GetBonds():
        p1, p2 = conf.GetAtomPosition(b.GetBeginAtomIdx()), conf.GetAtomPosition(b.GetEndAtomIdx())
        d = ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5
        if d > 1e-6:
            lens.append(d)
    return sum(lens) / len(lens) if lens else _BOND_LEN


def _scale_conformer(mol, factor: float):
    conf = mol.GetConformer()
    for i in range(mol.GetNumAtoms()):
        p = conf.GetAtomPosition(i)
        conf.SetAtomPosition(i, Point3D(p.x * factor, p.y * factor, 0.0))


def _rotate_translate_conformer(mol, cos_t: float, sin_t: float, dx: float, dy: float):
    """先绕原点旋转（cos/sin），再平移 (dx,dy)；z 归零"""
    conf = mol.GetConformer()
    for i in range(mol.GetNumAtoms()):
        p = conf.GetAtomPosition(i)
        conf.SetAtomPosition(i, Point3D(p.x * cos_t - p.y * sin_t + dx,
                                        p.x * sin_t + p.y * cos_t + dy, 0.0))


def _merge_fragment(base, frag, skip=(), map_to=None):
    """把 frag 并入 base（保留键类型）；skip 里的 frag 原子不新建，其键改接到 map_to[旧序号]"""
    rw = Chem.RWMol(base)
    if rw.GetNumConformers() == 0:
        rw.AddConformer(Chem.Conformer(rw.GetNumAtoms()), assignId=True)
    conf = rw.GetConformer()
    fconf = frag.GetConformer()
    map_to = map_to or {}
    old2new = {}
    for atom in frag.GetAtoms():
        i = atom.GetIdx()
        if i in skip:
            continue
        new_atom = Chem.Atom(atom.GetAtomicNum())
        new_atom.SetFormalCharge(atom.GetFormalCharge())
        new_atom.SetNoImplicit(False)
        ni = rw.AddAtom(new_atom)
        p = fconf.GetAtomPosition(i)
        conf.SetAtomPosition(ni, Point3D(p.x, p.y, 0.0))
        old2new[i] = ni
    for bond in frag.GetBonds():
        a1, a2 = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        n1 = old2new.get(a1, map_to.get(a1))
        n2 = old2new.get(a2, map_to.get(a2))
        if n1 is None or n2 is None or n1 == n2:
            continue
        if rw.GetBondBetweenAtoms(int(n1), int(n2)) is not None:
            continue
        rw.AddBond(int(n1), int(n2), bond.GetBondType())
    conf.Set3D(False)
    return rw.GetMol()


def _ring_fragment(key: str):
    """按环模板生成带 2D 坐标的片段（键长归一化到标准键长，芳香环先 Kekulize）"""
    smi = RING_SMILES.get((key or '').lower())
    if not smi:
        raise ValueError(f'未知环模板: {key}')
    frag = Chem.MolFromSmiles(smi)
    if frag is None:
        raise ValueError(f'环模板无法构建: {key}')
    AllChem.Compute2DCoords(frag)
    try:
        Chem.Kekulize(frag, clearAromaticFlags=True)
    except Exception:                             # noqa: BLE001
        pass
    mean = _mean_bond_length(frag)
    if mean > 1e-6:
        _scale_conformer(frag, _BOND_LEN / mean)
    conf = frag.GetConformer()
    cx = sum(conf.GetAtomPosition(i).x for i in range(frag.GetNumAtoms())) / frag.GetNumAtoms()
    cy = sum(conf.GetAtomPosition(i).y for i in range(frag.GetNumAtoms())) / frag.GetNumAtoms()
    _rotate_translate_conformer(frag, 1.0, 0.0, -cx, -cy)   # 质心移到原点
    return frag


def add_ring(mol, key: str, x: float = 0.0, y: float = 0.0, attach=None):
    """放一个环模板：attach 为空 → 放在 (x,y)；attach 为原子序号 → 该原子并入环中（稠合/螺环）"""
    frag = _ring_fragment(key)
    label = RING_LABELS.get((key or '').lower(), key)
    base = Chem.Mol(mol)
    if base.GetNumAtoms() == 0:
        # 空画布：直接放环
        frag2 = Chem.Mol(frag)
        _rotate_translate_conformer(frag2, 1.0, 0.0, float(x), float(y))
        return _finalize(frag2, f'已放置{label}（{frag2.GetNumAtoms()} 个原子）')

    if base.GetNumConformers() == 0:
        base = layout_2d(base)
    attach = None if attach is None or int(attach) < 0 else int(attach)
    fconf = frag.GetConformer()
    if attach is None:
        _rotate_translate_conformer(frag, 1.0, 0.0, float(x), float(y))
        merged = _merge_fragment(base, frag)
        m, note = _finalize(merged, f'已放置{label}')
        return m, note

    # ===== 与已有原子稠合：环上离点击点最近的顶点并入该原子 =====
    conf = base.GetConformer()
    ap = conf.GetAtomPosition(attach)
    # 点击点相对目标原子的方向（把环摆在点击的那一侧）
    dx, dy = float(x) - ap.x, float(y) - ap.y
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        # 没给点击方向：躲开已有取代基
        dx = dy = 0.0
        for nb in base.GetAtomWithIdx(attach).GetNeighbors():
            np_ = conf.GetAtomPosition(nb.GetIdx())
            dx -= np_.x - ap.x
            dy -= np_.y - ap.y
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            dx = 1.0
    want = math.atan2(dy, dx)
    # 选顶点：取“背对点击方向”的那个环原子（它落到目标原子上后，环身正好朝点击方向展开）
    back = want + math.pi
    best_k, best_score = 0, None
    for i in range(frag.GetNumAtoms()):
        p = fconf.GetAtomPosition(i)
        if abs(p.x) < 1e-9 and abs(p.y) < 1e-9:
            continue
        score = abs(_ang_diff(back, math.atan2(p.y, p.x)))
        if best_score is None or score < best_score:
            best_k, best_score = i, score
    kp = fconf.GetAtomPosition(best_k)
    # 旋转：让 best_k 落在背对点击的方向上，再平移使 best_k 与目标原子重合
    rot = back - math.atan2(kp.y, kp.x)
    _rotate_translate_conformer(frag, math.cos(rot), math.sin(rot), 0.0, 0.0)
    # 旋转是绕原点做的，再按 best_k 的新位置做校正平移
    kp2 = frag.GetConformer().GetAtomPosition(best_k)
    _rotate_translate_conformer(frag, 1.0, 0.0, float(ap.x) - kp2.x, float(ap.y) - kp2.y)
    merged = _merge_fragment(base, frag, skip={best_k}, map_to={best_k: attach})
    m, note = _finalize(merged, f'已在原子 {attach} 上稠合{label}')
    return m, note


def _ang_diff(a: float, b: float) -> float:
    d = (a - b + math.pi) % (2 * math.pi) - math.pi
    return d


# ============ 导出给前端 ============

def validity_of(mol):
    """结构是否能通过 RDKit 净化（价键/芳香性检查）→ (是否合法, 原因)

    编辑过程中允许出现不合法的中间态（例如手里画到一半的 5 价碳），但要让界面能提示用户。
    注意：失败信息由 _finalize / _mol_from_block 在净化那一刻打在分子上（_MLSValenceError）——
    之后再净化同一个对象可能因为属性缓存被"修好"而看不出问题，所以以那个标记为准。
    """
    if mol is None or mol.GetNumAtoms() == 0:
        return True, ''
    try:
        if mol.HasProp('_MLSValenceError'):
            return False, mol.GetProp('_MLSValenceError')
    except Exception:                             # noqa: BLE001
        pass
    try:
        Chem.SanitizeMol(Chem.Mol(mol))
        return True, ''
    except Exception as e:                        # noqa: BLE001
        msg = str(e).splitlines()[0].strip() if str(e) else '结构未通过价键检查'
        return False, msg


def mark_invalid(mol, message: str):
    """把净化失败的原因记在分子上，供 mol_to_dict 输出 valid/valid_error"""
    try:
        mol.SetProp('_MLSValenceError', message)
    except Exception:                             # noqa: BLE001
        pass
    return mol


def descriptors_of(mol):
    """「化学数据」面板用的分子描述符（对标 MolView 的 Chemical data）"""
    out = {
        'formula': '', 'mw': 0, 'exact_mass': 0, 'charge': 0,
        'n_atoms': 0, 'n_heavy': 0, 'n_bonds': 0, 'elements': [],
        'tpsa': 0, 'hbd': 0, 'hba': 0, 'rotatable': 0,
        'rings': 0, 'aromatic_rings': 0, 'logp': 0,
        'smiles': '', 'inchi': '', 'inchikey': '',
    }
    if mol is None or mol.GetNumAtoms() == 0:
        return out
    try:
        m = Chem.Mol(mol)
        m.UpdatePropertyCache(strict=False)
    except Exception:                             # noqa: BLE001
        m = mol

    def _f(fn, default=0.0):
        try:
            return round(float(fn(m)), 3)
        except Exception:                         # noqa: BLE001
            return default

    def _i(fn, default=0):
        try:
            return int(fn(m))
        except Exception:                         # noqa: BLE001
            return default

    out['formula'] = _str(lambda: rdMolDescriptors.CalcMolFormula(m))
    out['mw'] = _f(Descriptors.MolWt)
    out['exact_mass'] = _f(Descriptors.ExactMolWt)
    out['charge'] = _i(Chem.GetFormalCharge)
    out['n_atoms'] = m.GetNumAtoms()
    out['n_heavy'] = m.GetNumHeavyAtoms()
    out['n_bonds'] = m.GetNumBonds()
    out['tpsa'] = _f(rdMolDescriptors.CalcTPSA)
    out['hbd'] = _i(rdMolDescriptors.CalcNumHBD)
    out['hba'] = _i(rdMolDescriptors.CalcNumHBA)
    out['rotatable'] = _i(rdMolDescriptors.CalcNumRotatableBonds)
    out['rings'] = _i(rdMolDescriptors.CalcNumRings)
    out['aromatic_rings'] = _i(rdMolDescriptors.CalcNumAromaticRings)
    out['logp'] = _f(Descriptors.MolLogP)
    out['smiles'] = _str(lambda: Chem.MolToSmiles(Chem.RemoveHs(m)))
    out['inchi'] = _str(lambda: Chem.MolToInchi(m))
    out['inchikey'] = _str(lambda: Chem.InchiToInchiKey(out['inchi']) if out['inchi'] else '')
    counts = {}
    for a in m.GetAtoms():
        counts[a.GetSymbol()] = counts.get(a.GetSymbol(), 0) + 1
    order = [s for s in ('C', 'H', 'N', 'O', 'S', 'P', 'F', 'Cl', 'Br', 'I') if s in counts]
    order += sorted(k for k in counts if k not in order)
    out['elements'] = [{'symbol': s, 'count': counts[s]} for s in order]
    return out


def _str(fn, default=''):
    try:
        v = fn()
        return v if isinstance(v, str) else ('' if v is None else str(v))
    except Exception:                             # noqa: BLE001
        return default


def gasteiger_charges(mol):
    """Gasteiger 原子电荷（对标 MolView/Jmol 的 Charge）"""
    if mol is None or mol.GetNumAtoms() == 0:
        return []
    m = Chem.Mol(mol)
    try:
        AllChem.ComputeGasteigerCharges(m, nIter=20)
    except Exception:                             # noqa: BLE001
        return []
    out = []
    for a in m.GetAtoms():
        try:
            q = float(a.GetProp('_GasteigerCharge'))
        except Exception:                         # noqa: BLE001
            q = 0.0
        if not math.isfinite(q):
            q = 0.0
        out.append({'index': a.GetIdx(), 'charge': q})
    return out


def overall_dipole(mol, charges=None):
    """用 Gasteiger 电荷 + 坐标估整体偶极矩（Debye）：μ = 4.8032 Σ q_i r_i"""
    if mol is None or mol.GetNumAtoms() == 0 or mol.GetNumConformers() == 0:
        return None
    if charges is None:
        charges = gasteiger_charges(mol)
    if not charges:
        return None
    conf = mol.GetConformer()
    qmap = {c['index']: c['charge'] for c in charges}
    mx = my = mz = 0.0
    for a in mol.GetAtoms():
        p = conf.GetAtomPosition(a.GetIdx())
        q = qmap.get(a.GetIdx(), 0.0)
        mx += q * p.x
        my += q * p.y
        mz += q * p.z
    k = 4.8032
    mx, my, mz = mx * k, my * k, mz * k
    return {'x': mx, 'y': my, 'z': mz, 'magnitude': math.sqrt(mx * mx + my * my + mz * mz)}


# ============ PubChem 检索（对标 MolView 的搜索框） ============

def fetch_pubchem(query: str, kind: str = 'name', timeout: int = 20):
    """按 名称 / CID / SMILES 从 PubChem 取一个结构（2D 坐标），返回 (mol, name)"""
    import urllib.parse
    import urllib.request

    q = (query or '').strip()
    if not q:
        raise ValueError('请输入名称、CID 或 SMILES')
    kind = (kind or 'name').lower()
    if kind not in ('name', 'cid', 'smiles'):
        kind = 'name'
    url = ('https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/'
           f'{kind}/{urllib.parse.quote(q, safe="")}/SDF?record_type=2d')
    req = urllib.request.Request(url, headers={'User-Agent': 'MLS/26.9 (molecular-lab-suite)'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode('utf-8', 'replace')
    except Exception as e:                        # noqa: BLE001
        raise ValueError(f'PubChem 检索失败（{e}）')
    if '$$$$' not in text and 'M  END' not in text:
        raise ValueError('PubChem 未返回结构（名称是否正确？）')
    mol = Chem.MolFromMolBlock(text, removeHs=False, sanitize=True)
    if mol is None:
        mol = Chem.MolFromMolBlock(text, removeHs=False, sanitize=False)
    if mol is None:
        raise ValueError('PubChem 返回的结构无法解析')
    try:
        mol = Chem.RemoveHs(mol)                  # 画布按骨架显示（和 MolView 一致），需要时再「加氢」
    except Exception:                             # noqa: BLE001
        pass
    return mol, q

def atoms_of(mol):
    """原子列表（坐标保留完整精度；molblock 只有 4 位小数，导出 .mls 时用它）

    n_h / implicit_h / charge 供 2D 绘制标注用（对标 ChemDraw 的原子标签，如 OH、NH2、CH3）
    """
    conf = mol.GetConformer() if mol.GetNumConformers() else None
    out = []
    for atom in mol.GetAtoms():
        p = conf.GetAtomPosition(atom.GetIdx()) if conf else Point3D(0, 0, 0)
        try:
            n_h = atom.GetTotalNumHs()
            n_implicit = atom.GetNumImplicitHs()
        except Exception:                         # noqa: BLE001 - 未净化时可能取不到
            n_h, n_implicit = 0, 0
        out.append({
            'index': atom.GetIdx(),
            'symbol': atom.GetSymbol(),
            'x': p.x, 'y': p.y, 'z': p.z,
            'charge': atom.GetFormalCharge(),
            'aromatic': atom.GetIsAromatic(),
            'heavy_degree': atom.GetDegree(),
            'n_h': int(n_h),
            'implicit_h': int(n_implicit),
            'is_h': atom.GetAtomicNum() == 1,
        })
    return out


def bonds_of(mol):
    """键列表；额外给出 2D 绘制需要的显示信息：

    display_order  芳香键按 Kekulé 交替单双键显示（和 MolView / ChemDraw 一致）
    in_ring/flip   环内双键的第二条线画在环内侧（flip 决定法线方向）
    """
    # Kekulé 显示顺序
    display = {}
    try:
        m = Chem.Mol(mol)
        Chem.Kekulize(m, clearAromaticFlags=True)
        for b in m.GetBonds():
            display[(b.GetBeginAtomIdx(), b.GetEndAtomIdx())] = int(b.GetBondTypeAsDouble())
            display[(b.GetEndAtomIdx(), b.GetBeginAtomIdx())] = int(b.GetBondTypeAsDouble())
    except Exception:                             # noqa: BLE001
        pass

    # 环信息：判断键是否在环上、以及环中心在哪一侧
    rings = []
    try:
        ri = mol.GetRingInfo()
        rings = [list(r) for r in ri.AtomRings()]
    except Exception:                             # noqa: BLE001
        pass
    conf = mol.GetConformer() if mol.GetNumConformers() else None

    out = []
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        order = float(b.GetBondTypeAsDouble())
        disp = display.get((i, j), int(round(order)) if order < 1.4 else 1)
        in_ring = False
        flip = False
        candidates = [r for r in rings if i in r and j in r and len(r) <= 8]
        if candidates and conf is not None:
            in_ring = True
            pi, pj = conf.GetAtomPosition(i), conf.GetAtomPosition(j)
            mx, my = (pi.x + pj.x) / 2, (pi.y + pj.y) / 2
            dx, dy = pj.x - pi.x, pj.y - pi.y
            # 多个环共用这条键时取环心离键中点最近的那个（把第二条线画在它内侧）
            ring = min(candidates, key=lambda r: (
                (sum(conf.GetAtomPosition(k).x for k in r) / len(r) - mx) ** 2 +
                (sum(conf.GetAtomPosition(k).y for k in r) / len(r) - my) ** 2))
            cx = sum(conf.GetAtomPosition(k).x for k in ring) / len(ring)
            cy = sum(conf.GetAtomPosition(k).y for k in ring) / len(ring)
            # 前端画布 y 轴向下，这里按屏幕坐标判定法线方向（保证 flip 在前端用法一致）
            flip = ((cx - mx) * dy + (cy - my) * (-dx)) < 0
        out.append({
            'a': i, 'b': j,
            'order': order,
            'aromatic': b.GetIsAromatic(),
            'display_order': disp if 1 <= disp <= 3 else 1,
            'in_ring': in_ring,
            'flip': flip,
        })
    return out


def mol_to_dict(mol, show_indices: bool = False):
    three_d = has_3d(mol)
    try:
        smiles = Chem.MolToSmiles(Chem.RemoveHs(mol)) if mol.GetNumAtoms() else ''
    except Exception:
        smiles = ''
    try:
        formula = rdMolDescriptors.CalcMolFormula(mol) if mol.GetNumAtoms() else ''
        mw = round(Descriptors.MolWt(mol), 3) if mol.GetNumAtoms() else 0
    except Exception:
        formula, mw = '', 0
    molblock = safe_molblock(mol)
    valid, valid_error = validity_of(mol)
    data = {
        'molblock': molblock,
        'atoms': atoms_of(mol),
        'bonds': bonds_of(mol),
        'has3d': three_d,
        'is3d': three_d,
        'is2d': not three_d,
        'valid': valid,
        'valid_error': valid_error,
        'formula': formula,
        'mw': mw,
        'smiles': smiles,
        'n_atoms': mol.GetNumAtoms(),
        'n_bonds': mol.GetNumBonds(),
        'charge': Chem.GetFormalCharge(mol) if mol.GetNumAtoms() else 0,
    }
    return data


def safe_molblock(mol) -> str:
    """写 molblock：先保证属性缓存/芳香性一致，避免写出坏数据"""
    m = Chem.Mol(mol)
    try:
        m.UpdatePropertyCache(strict=False)
    except Exception:
        pass
    try:
        return Chem.MolToMolBlock(m)
    except Exception:
        pass
    # 芳香性/价键不一致时，先 Kekulize 再写
    try:
        m2 = Chem.Mol(mol)
        Chem.Kekulize(m2, clearAromaticFlags=True)
        m2.UpdatePropertyCache(strict=False)
        return Chem.MolToMolBlock(m2)
    except Exception:
        return ''


def atoms_for_export(mol):
    """给 .mls / 输入文件用的 (sym, x, y, z) 列表"""
    if mol.GetNumConformers() == 0:
        raise ValueError('分子没有坐标，无法导出（请先做 3D 优化）')
    conf = mol.GetConformer()
    return [(a.GetSymbol(), conf.GetAtomPosition(a.GetIdx()).x,
             conf.GetAtomPosition(a.GetIdx()).y, conf.GetAtomPosition(a.GetIdx()).z)
            for a in mol.GetAtoms()]


# ============ 编辑操作 ============

def _set_position(mol, idx: int, x: float, y: float, z: float):
    conf = mol.GetConformer() if mol.GetNumConformers() else None
    if conf is None:
        mol.AddConformer(Chem.Conformer(mol.GetNumAtoms()), assignId=True)
        conf = mol.GetConformer()
    conf.SetAtomPosition(int(idx), Point3D(float(x), float(y), float(z)))
    conf.Set3D(True)


def _finalize(mol, note: str = ''):
    """编辑后统一收尾：重新净化（感知芳香性/隐式氢），必要时给出提示"""
    m = Chem.Mol(mol)
    try:
        Chem.SanitizeMol(m)
        try:
            if m.HasProp('_MLSValenceError'):
                m.ClearProp('_MLSValenceError')
        except Exception:                         # noqa: BLE001
            pass
    except Exception as e:                        # noqa: BLE001 - 允许带瑕疵继续编辑
        try:
            m.UpdatePropertyCache(strict=False)
        except Exception:
            pass
        first = str(e).splitlines()[0][:70] if str(e) else '未知原因'
        mark_invalid(m, first)
        note = (note + '；' if note else '') + f'结构未完全通过净化（{first}）'
    return m, note


def apply_edit(mol, op: str, payload: dict):
    """在分子上执行一次编辑，返回 (新 mol, 提示)

    注意：编辑前先 Kekulize（清掉芳香标记），编辑后再 Sanitize 重新感知芳香性——
    否则对芳香体系加键/删原子会让 molblock 无法写出。
    """
    note = ''
    payload = payload or {}
    base = Chem.Mol(mol)
    try:
        Chem.Kekulize(base, clearAromaticFlags=True)
    except Exception:
        base = Chem.Mol(mol)
    rw = Chem.RWMol(base)

    if op == 'add_atom':
        sym = (payload.get('element') or 'C').capitalize()
        z = SYMBOL_TO_ATOMIC_NUMBER.get(sym)
        if z is None:
            raise ValueError(f'不支持的元素: {sym}')
        idx = rw.AddAtom(Chem.Atom(int(z)))
        near = payload.get('near')
        x, y, zc = 0.0, 0.0, 0.0
        if payload.get('x') is not None and payload.get('y') is not None:
            # 2D 绘制：按画布点击位置放置（z 固定 0，构象标记为 2D）
            x, y, zc = float(payload.get('x')), float(payload.get('y')), float(payload.get('z') or 0.0)
        elif mol.GetNumConformers():
            conf = mol.GetConformer()
            if near is not None and 0 <= int(near) < mol.GetNumAtoms():
                bp = conf.GetAtomPosition(int(near))
                x, y, zc = bp.x + 1.4, bp.y + 0.4, bp.z + 0.4
            else:
                ps = conf.GetPositions()
                if len(ps):
                    x = float(ps[:, 0].mean())
                    y = float(ps[:, 1].mean())
                    zc = float(ps[:, 2].mean())
        mol2 = rw.GetMol()
        _set_position(mol2, idx, x, y, zc)
        if payload.get('x') is not None:
            mol2.GetConformer().Set3D(False)
        return _finalize(mol2, f'已添加 {sym}（原子序号 {idx}）')

    if op == 'set_charge':
        idx = int(payload.get('index', -1))
        if not (0 <= idx < rw.GetNumAtoms()):
            raise ValueError('原子序号超出范围')
        chg = int(payload.get('charge', 0))
        atom = rw.GetAtomWithIdx(idx)
        atom.SetFormalCharge(max(-4, min(4, chg)))
        atom.SetNoImplicit(False)
        return _finalize(rw.GetMol(), f'原子 {idx} 电荷改为 {atom.GetFormalCharge()}')

    if op == 'add_ring':
        return add_ring(
            mol,
            payload.get('ring') or 'benzene',
            x=float(payload.get('x') or 0.0),
            y=float(payload.get('y') or 0.0),
            attach=payload.get('attach'),
        )

    if op == 'remove_atom':
        idx = int(payload.get('index', -1))
        if not (0 <= idx < rw.GetNumAtoms()):
            raise ValueError('原子序号超出范围')
        rw.RemoveAtom(idx)
        return _finalize(rw.GetMol(), '已删除原子（后续原子序号已重排）')

    if op == 'set_element':
        idx = int(payload.get('index', -1))
        sym = (payload.get('element') or '').capitalize()
        z = SYMBOL_TO_ATOMIC_NUMBER.get(sym)
        if z is None:
            raise ValueError(f'不支持的元素: {sym}')
        if not (0 <= idx < rw.GetNumAtoms()):
            raise ValueError('原子序号超出范围')
        atom = rw.GetAtomWithIdx(idx)
        atom.SetAtomicNum(int(z))
        atom.SetNoImplicit(False)
        return _finalize(rw.GetMol(), f'原子 {idx} 已改为 {sym}')

    if op == 'set_position':
        idx = int(payload.get('index', -1))
        if not (0 <= idx < rw.GetNumAtoms()):
            raise ValueError('原子序号超出范围')
        mol2 = rw.GetMol()
        _set_position(mol2, idx, payload.get('x', 0), payload.get('y', 0), payload.get('z', 0))
        return _finalize(mol2, f'原子 {idx} 坐标已更新')

    if op == 'add_bond':
        a, b = int(payload.get('a', -1)), int(payload.get('b', -1))
        order = int(float(payload.get('order', 1)))
        if a == b or not (0 <= a < rw.GetNumAtoms()) or not (0 <= b < rw.GetNumAtoms()):
            raise ValueError('请选择两个不同的原子')
        if rw.GetBondBetweenAtoms(a, b) is not None:
            raise ValueError('这两个原子之间已经有键')
        bt = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE,
              3: Chem.BondType.TRIPLE}.get(order, Chem.BondType.SINGLE)
        rw.AddBond(a, b, bt)
        return _finalize(rw.GetMol(), f'已建立键 {a}-{b}（键级 {order}）')

    if op == 'remove_bond':
        a, b = int(payload.get('a', -1)), int(payload.get('b', -1))
        if rw.GetBondBetweenAtoms(a, b) is None:
            raise ValueError('这两个原子之间没有键')
        rw.RemoveBond(a, b)
        return _finalize(rw.GetMol(), f'已删除键 {a}-{b}')

    if op == 'set_bond_order':
        a, b = int(payload.get('a', -1)), int(payload.get('b', -1))
        order = int(payload.get('order', 1))
        bond = rw.GetBondBetweenAtoms(a, b)
        if bond is None:
            raise ValueError('这两个原子之间没有键')
        bt = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE,
              3: Chem.BondType.TRIPLE}.get(order, Chem.BondType.SINGLE)
        bond.SetBondType(bt)
        return _finalize(rw.GetMol(), f'键 {a}-{b} 键级改为 {order}')

    if op == 'add_hs':
        mol2 = Chem.AddHs(rw.GetMol(), addCoords=True)
        return _finalize(mol2, '已加氢')

    if op == 'remove_hs':
        mol2 = Chem.RemoveHs(rw.GetMol())
        return _finalize(mol2, '已去氢')

    raise ValueError(f'未知编辑操作: {op}')
