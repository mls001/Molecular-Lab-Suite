# 分子文件读取 / 编辑 / 生成输入文件（Gaussian 与 ORCA）
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import input_builder as ib
from app.core import mol_io as mio

router = APIRouter()


# ============ 列表 / 目录 ============

class ListMolsRequest(BaseModel):
    folder: Optional[str] = None
    extensions: Optional[List[str]] = None
    recursive: bool = False


@router.get("/presets")
async def presets():
    """界面需要的所有预设与支撑格式（环模板带原子/键，前端据此直接画缩略图）"""
    rings = []
    for key, _smi, label in mio.RING_TEMPLATES:
        item = {'id': key, 'label': label, 'atoms': [], 'bonds': []}
        try:
            data = mio.mol_to_dict(mio._ring_fragment(key))
            item['atoms'] = data['atoms']
            item['bonds'] = data['bonds']
        except Exception:                          # noqa: BLE001 - 画不出缩略图不影响功能
            pass
        rings.append(item)
    return {
        'mols_dir': mio.mols_dir(),
        'supported_ext': mio.SUPPORTED_EXT,
        'orca_presets': ib.ORCA_PRESETS,
        'gaussian_modes': ib.GAUSSIAN_MODES,
        'orca_basis_presets': ib.ORCA_BASIS_PRESETS,
        'orca_func_presets': ib.ORCA_FUNC_PRESETS,
        'gaussian_basis_presets': ib.GAUSSIAN_BASIS_PRESETS,
        'gaussian_func_presets': ib.GAUSSIAN_FUNC_PRESETS,
        'rings': rings,
    }


@router.get("/mols")
async def list_mols():
    """Mols 目录（.exe 同级）及其中的 .mls 文件"""
    folder = mio.mols_dir()
    return {'dir': folder, 'files': mio.list_mls(folder)}


@router.post("/list")
async def list_molecules(req: ListMolsRequest):
    """列出目录下的分子文件；folder 为空时列 Mols 目录"""
    folder = req.folder or mio.mols_dir()
    if not os.path.isdir(folder):
        raise HTTPException(status_code=400, detail=f'目录不存在: {folder}')
    exts = [e.lower() for e in (req.extensions or mio.SUPPORTED_EXT)]
    files = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in exts:
                    files.append({
                        'name': entry.name,
                        'path': entry.path,
                        'ext': ext,
                        'size': entry.stat().st_size,
                        'is_mls': ext == '.mls',
                    })
    except PermissionError:
        raise HTTPException(status_code=403, detail=f'没有权限读取目录: {folder}')
    files.sort(key=lambda f: (not f['is_mls'], f['name'].lower()))
    return {'folder': folder, 'files': files}


# ============ 打开 / 转换 ============

class OpenRequest(BaseModel):
    path: Optional[str] = None
    content: Optional[str] = None
    ext: Optional[str] = None
    name: Optional[str] = None
    charge: int = 0
    auto_3d: bool = True


@router.post("/open")
async def open_molecule(req: OpenRequest):
    """任意格式 → 原子/键/信息 + 2D 图；缺 3D 时按需生成合理结构"""
    try:
        mol, warning, meta = mio.read_molecule(req.path, req.content, req.ext, req.charge)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:                        # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))

    notes = [warning] if warning else []
    if req.auto_3d and mol.GetNumAtoms() and not mio.has_3d(mol):
        mol, note = mio.ensure_3d(mol)
        if note:
            notes.append(note)

    data = mio.mol_to_dict(mol)
    data['name'] = os.path.splitext(os.path.basename(req.path or req.name or 'molecule'))[0]
    data['source'] = req.path or req.name or ''
    data['charge'] = req.charge if req.charge else meta.get('charge', 0)
    data['mult'] = meta.get('mult', 1)
    data['note'] = '；'.join([n for n in notes if n])
    return data


class MolBlockRequest(BaseModel):
    molblock: str
    charge: int = 0


class EmbedRequest(MolBlockRequest):
    ff: str = 'MMFF94'
    add_hs: bool = True
    optimize: bool = True                     # False = 只做 ETKDG 快速嵌入（大分子实时同步用）


@router.post("/layout2d")
async def layout_2d(req: MolBlockRequest):
    """生成理想 2D 坐标（对标 ChemDraw 的 Clean Up Structure），供 2D 绘制画布使用"""
    mol = _mol_from_block(req.molblock)
    mol2 = mio.layout_2d(mol)
    data = mio.mol_to_dict(mol2)
    data['note'] = '已生成 2D 坐标（可直接在 2D 画布上修改）'
    return data


@router.post("/embed3d")
async def embed_3d(req: EmbedRequest):
    """用 RDKit 生成合理的 3D 结构（ETKDG + 力场优化）；空结构直接返回空（画布被擦空的情况）"""
    mol = _mol_from_block(req.molblock, allow_empty=True)
    if mol.GetNumAtoms() == 0:
        return mio.mol_to_dict(mol)
    notes = []
    if req.add_hs and any(a.GetAtomicNum() == 1 for a in mol.GetAtoms()) is False:
        mol = _safe_add_hs(mol)
    if not req.optimize:
        mol, note = mio.ensure_3d(mol, optimize=False)
    elif mio.has_3d(mol):
        # 已有 3D 也重新优化一次，保证几何合理
        mol, note = _optimize(mol, req.ff)
    else:
        mol, note = mio.ensure_3d(mol, req.ff)
    if note:
        notes.append(note)
    data = mio.mol_to_dict(mol)
    data['note'] = '；'.join(notes)
    return data


def _safe_add_hs(mol):
    try:
        from rdkit import Chem
        return Chem.AddHs(mol, addCoords=True)
    except Exception:
        return mol


def _optimize(mol, ff='MMFF94'):
    from rdkit.Chem import AllChem
    m = _safe_add_hs(mol)
    note = ''
    try:
        if ff.upper() == 'UFF' or not AllChem.MMFFHasAllMoleculeParams(m):
            AllChem.UFFOptimizeMolecule(m, maxIters=800)
            note = 'UFF 优化完成'
        else:
            AllChem.MMFFOptimizeMolecule(m, maxIters=800)
            note = 'MMFF94 优化完成'
    except Exception as e:                        # noqa: BLE001
        note = f'力场优化跳过（{e}）'
    return m, note


def _mol_from_block(molblock: str, allow_empty: bool = False):
    from rdkit import Chem
    if allow_empty and not (molblock or '').strip():
        return Chem.Mol()                         # 空画布：从零开始绘制
    mol = Chem.MolFromMolBlock(molblock or '', removeHs=False, sanitize=False)
    if mol is None:
        raise HTTPException(status_code=400, detail='分子数据无法解析')
    try:
        Chem.SanitizeMol(mol)
    except Exception as e:                        # noqa: BLE001 - 允许带瑕疵继续编辑
        try:
            mol.UpdatePropertyCache(strict=False)
        except Exception:
            pass
        mio.mark_invalid(mol, str(e).splitlines()[0].strip() if str(e) else '结构未通过价键检查')
    return mol


# ============ 编辑 ============

class EditRequest(MolBlockRequest):
    op: str
    payload: dict = {}


@router.post("/edit")
async def edit_molecule(req: EditRequest):
    """增删原子/键、改元素/电荷、改键级、加环模板、加氢去氢、改坐标

    允许空 molblock（2D 画布从零开始绘制：先放原子/环）。
    """
    mol = _mol_from_block(req.molblock, allow_empty=True)
    try:
        mol2, note = mio.apply_edit(mol, req.op, req.payload)
    except Exception as e:                        # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
    data = mio.mol_to_dict(mol2)
    data['note'] = note
    return data


# ============ 保存 .mls ============

class SaveMlsRequest(BaseModel):
    name: str
    molblock: Optional[str] = None
    atoms: Optional[List[dict]] = None
    directory: Optional[str] = None


@router.post("/save-mls")
async def save_mls(req: SaveMlsRequest):
    """把当前坐标按 "元素 x y z" 保存为 .mls（默认写入 .exe 同级的 Mols 目录）"""
    if req.molblock:
        mol = _mol_from_block(req.molblock)
        try:
            atoms = mio.atoms_for_export(mol)
        except Exception as e:                    # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(e))
    elif req.atoms:
        atoms = [(a.get('symbol', 'C'), float(a.get('x', 0)), float(a.get('y', 0)),
                  float(a.get('z', 0))) for a in req.atoms]
    else:
        raise HTTPException(status_code=400, detail='缺少分子坐标')
    if not atoms:
        raise HTTPException(status_code=400, detail='分子没有原子')
    try:
        path = mio.save_mls(req.name, atoms, req.directory)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f'保存失败: {e}')
    return {'path': path, 'name': os.path.basename(path),
            'dir': os.path.dirname(path), 'n_atoms': len(atoms)}


# ============ 生成 / 保存输入文件 ============

class ToInputRequest(BaseModel):
    molblock: Optional[str] = None
    path: Optional[str] = None
    target: str = 'gaussian'                      # gaussian | orca
    charge: int = 0
    mult: int = 1
    functional: str = 'm062x'
    basis: str = '6-31g(d,p)'
    calc: str = '#p opt'                          # Gaussian 计算模式
    preset: str = 'soc_tddft'                     # ORCA 预设
    nstates: int = 10
    mem: str = '20GB'
    nproc: str = '8'
    maxcore: int = 2500
    title: str = ''
    extra_keywords: str = ''
    extra_blocks: str = ''
    filename: Optional[str] = None


@router.post("/to-input")
async def to_input(req: ToInputRequest):
    """把分子坐标写成 Gaussian(.gjf) 或 ORCA(.inp) 输入文件内容"""
    if req.molblock:
        mol = _mol_from_block(req.molblock)
        base = req.title or 'molecule'
    elif req.path:
        if not os.path.exists(req.path):
            raise HTTPException(status_code=404, detail=f'文件不存在: {req.path}')
        mol, _warning, _meta = mio.read_molecule(req.path, charge=req.charge)
        base = os.path.splitext(os.path.basename(req.path))[0]
    else:
        raise HTTPException(status_code=400, detail='缺少分子（molblock 或 path）')

    if not mol.GetNumConformers() or not mio.has_3d(mol):
        mol, _note = mio.ensure_3d(mol)
    try:
        atoms = mio.atoms_for_export(mol)
    except Exception as e:                        # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))

    name = req.filename or base
    if req.target.lower().startswith('orca'):
        content = ib.build_orca(
            atoms, charge=req.charge, mult=req.mult, functional=req.functional,
            basis=req.basis, preset=req.preset, nstates=req.nstates,
            maxcore=req.maxcore, nprocs=int(req.nproc or 1), title=req.title,
            extra_keywords=req.extra_keywords, extra_blocks=req.extra_blocks)
        filename = name if name.lower().endswith('.inp') else f'{name}.inp'
    else:
        content = ib.build_gaussian(
            atoms, charge=req.charge, mult=req.mult, functional=req.functional,
            basis=req.basis, calc=req.calc, mem=req.mem, nproc=req.nproc,
            chk_name=f'{name}.chk', title=req.title,
            extra_keywords=req.extra_keywords)
        filename = name if name.lower().endswith('.gjf') else f'{name}.gjf'
    return {'content': content, 'filename': filename, 'n_atoms': len(atoms),
            'target': 'orca' if req.target.lower().startswith('orca') else 'gaussian'}


class SaveInputRequest(BaseModel):
    folder: str
    filename: str
    content: str
    overwrite: bool = True


@router.post("/save-input")
async def save_input(req: SaveInputRequest):
    """把生成的输入文件写入指定目录"""
    if not req.folder:
        raise HTTPException(status_code=400, detail='缺少输出目录')
    name = os.path.basename(req.filename or 'input.gjf')
    try:
        os.makedirs(req.folder, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f'无法创建目录: {e}')
    path = os.path.join(req.folder, name)
    if os.path.exists(path) and not req.overwrite:
        raise HTTPException(status_code=400, detail='目标文件已存在')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(req.content)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f'写入失败: {e}')
    return {'path': path, 'name': name}


# ============ 化学数据 / 电荷 / 导出（对标 MolView） ============

@router.post("/descriptors")
async def descriptors(req: MolBlockRequest):
    """化学数据面板：分子式、分子量、精确质量、TPSA、LogP、InChI 等"""
    mol = _mol_from_block(req.molblock, allow_empty=True)
    data = mio.descriptors_of(mol)
    data['molblock'] = mio.safe_molblock(mol) if mol.GetNumAtoms() else ''
    return data


@router.post("/charges")
async def charges(req: MolBlockRequest):
    """Gasteiger 原子电荷 + 整体偶极（对标 MolView 的 Charge / Overall dipole）"""
    mol = _mol_from_block(req.molblock, allow_empty=True)
    ch = mio.gasteiger_charges(mol)
    dip = mio.overall_dipole(mol, ch)
    return {'charges': ch, 'dipole': dip}


class SaveFileRequest(BaseModel):
    folder: str
    filename: str
    content: Optional[str] = None        # 文本（.mol/.svg/.mls）
    content_base64: Optional[str] = None  # 二进制（.png）
    overwrite: bool = True


@router.post("/save-file")
async def save_file(req: SaveFileRequest):
    """导出：把文本或 base64 二进制内容写到用户选择的目录"""
    import base64
    if not req.folder:
        raise HTTPException(status_code=400, detail='缺少输出目录')
    name = os.path.basename(req.filename or 'export.dat')
    if not name:
        raise HTTPException(status_code=400, detail='缺少文件名')
    try:
        os.makedirs(req.folder, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f'无法创建目录: {e}')
    path = os.path.join(req.folder, name)
    if os.path.exists(path) and not req.overwrite:
        raise HTTPException(status_code=400, detail='目标文件已存在')
    try:
        if req.content_base64:
            blob = base64.b64decode(req.content_base64.split(',')[-1])
            with open(path, 'wb') as f:
                f.write(blob)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(req.content or '')
    except Exception as e:                        # noqa: BLE001
        raise HTTPException(status_code=400, detail=f'写入失败: {e}')
    return {'path': path, 'name': name, 'size': os.path.getsize(path)}


class FetchRequest(BaseModel):
    query: str
    kind: str = 'name'                   # name | cid | smiles


@router.post("/fetch")
async def fetch_structure(req: FetchRequest):
    """从 PubChem 检索结构（MolView 的搜索框）"""
    try:
        mol, name = mio.fetch_pubchem(req.query, req.kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:                        # noqa: BLE001
        raise HTTPException(status_code=400, detail=f'检索失败: {e}')
    data = mio.mol_to_dict(mol)
    data['name'] = name
    data['source'] = f'PubChem:{req.kind}:{req.query}'
    data['note'] = '已从 PubChem 载入（2D 结构，可点「转换为 3D」）'
    return data
