"""外部程序联用：Multiwfn 生成轨道 cube、VMD 渲染轨道图

设计要点：
- 只做「生成脚本 → 调用程序 → 收集产物 → 返回日志」，具体菜单/脚本都可从前端覆盖，
  这样不同 Multiwfn / VMD 版本的差异由用户在前端改脚本即可适配。
- 所有外部程序输出都回传给界面（日志区），出错时看得到原因。
"""
import glob
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import plot_config
from app.core.multiwfn_citation import citation_payload
from app.routers.tools import CANDIDATES, find_in_path

router = APIRouter()

# 产物目录后缀：轨道图 → <分子名>-Orbitals/，图片统一再进 PIC/
SUFFIX_ORBITALS = '-Orbitals'

# 绘图风格（VMD 脚本 / Tachyon 参数 / 分辨率 / Multiwfn 脚本）都在软件根目录的
# mls-plots.json 里，本模块只负责读取：
#   plot_config.vmd_template()      默认 VMD 脚本
#   plot_config.vmd_styles()        各风格 → (VMD 附加设定, tachyon 参数, 分辨率)
#   plot_config.multiwfn_template() 默认 Multiwfn 输入脚本
# 末尾由后端补 MWFN_TAIL（子菜单 0 返回主菜单、q 正常退出），否则 Multiwfn 停在提示上等
# 输入，stdin 耗尽就会 forrtl: severe (24) 崩溃。
MWFN_TAIL = ['0', 'q']


def find_program(folder: str, kind: str) -> str:
    """在指定目录里找可执行文件；目录里没有就去系统 PATH（环境变量）里找"""
    folder = (folder or '').strip()
    if folder and os.path.isdir(folder):
        for name in CANDIDATES.get(kind, []):
            p = os.path.join(folder, name)
            if os.path.isfile(p):
                return p
        # 目录里任意匹配名字的文件
        pats = {'multiwfn': ['*multiwfn*'], 'vmd': ['vmd*.exe', 'vmd'],
                'tachyon': ['tachyon*.exe', 'tachyon']}.get(kind, [])
        for pat in pats:
            hits = sorted(glob.glob(os.path.join(folder, pat)))
            if hits:
                return hits[0]
    # 目录没配或没找到 → 用系统 PATH 里注册的（很多用户已经把 Multiwfn / VMD 加进环境变量）
    return find_in_path(kind)


# 可直接被 Multiwfn 读取的波函数文件；.chk 必须先 formchk 转换
WAVEFN_EXTS = ('.fch', '.fchk', '.wfn', '.wfx', '.molden', '.47', '.gbw', '.mwfn')
WAVEFN_PRIORITY = ['.fch', '.fchk', '.wfx', '.molden', '.wfn', '.mwfn', '.47', '.gbw']
LOG_EXTS = ('.log', '.out')
# Gaussian 只有写了 gfinput（或 IOp(3/33=1)）才会打印基组；pop=full 才会打印轨道系数
BASIS_MARKERS = ('primitives', 'general basis input', 'shell types', 'ao basis set',
                 'basis set in the form of')
MO_MARKERS = ('molecular orbital coefficients', 'orbital coefficients:',
              'orbital energies and coefficients', 'alpha mo coefficients',
              'beta mo coefficients', 'mo coefficients')
# ORCA 的输出：基组要 %output Print[P_Basis]，轨道要 Print[P_MOs]（或直接用 .gbw）
ORCA_BASIS_MARKERS = ('basis set in input format', 'print[p_basis]', 'symmetry independent basis')
ORCA_MO_MARKERS = ('molecular orbitals', 'print[p_mos]', 'orbital energies and coefficients')
FORMCHK_NAMES = ['formchk.exe', 'formchk']


def _looks_like_orca(path: str) -> bool:
    """ORCA 输出的抬头有「* O   R   C   A *」"""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            head = f.read(16 * 1024).lower()
    except OSError:
        return False
    return ('o   r   c   a' in head or 'orca program' in head or 'scf settings:' in head)


def _has_markers(path: str, markers) -> bool:
    """在（可能很大的）文件里分块查找关键字，找到第一个即可返回"""
    todo = [m.lower() for m in markers]
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            while todo:
                chunk = f.read(2 * 1024 * 1024)
                if not chunk:
                    break
                low = chunk.lower()
                rest = []
                for m in todo:
                    if m in low:
                        return True
                    rest.append(m)
                todo = rest
    except OSError:
        return False
    return False


def scan_source(path: str) -> dict:
    """判断 Multiwfn 能不能从这个文件里读到波函数"""
    ext = os.path.splitext(path)[1].lower()
    info = {'path': path, 'ext': ext, 'basis': False, 'mo': False, 'kind': ext.lstrip('.')}
    if ext in WAVEFN_EXTS:
        info.update(ok=True, reason='')
        return info
    if ext == '.chk':
        info.update(ok=False, reason='.chk 是 Gaussian 检查点文件，Multiwfn 不能直接读，请先用 formchk 转成 .fchk')
        return info
    if ext in LOG_EXTS:
        orca = _looks_like_orca(path)
        info['orca'] = orca
        info['basis'] = _has_markers(path, ORCA_BASIS_MARKERS if orca else BASIS_MARKERS)
        info['mo'] = _has_markers(path, ORCA_MO_MARKERS if orca else MO_MARKERS)
        info['ok'] = bool(info['basis'] and info['mo'])
        if not info['ok']:
            miss = []
            if not info['basis']:
                miss.append('基组信息' + ('（%output Print[P_Basis] 2）' if orca else '（关键词 gfinput / IOp(3/33=1)）'))
            if not info['mo']:
                miss.append('轨道系数' + ('（%output Print[P_MOs] 1）' if orca else '（关键词 pop=full）'))
            info['reason'] = (('该 ORCA 输出' if orca else '该 LOG') + '里缺少 ' + '、'.join(miss)
                              + '，Multiwfn 无法从它读取波函数')
        return info
    # 其余格式交给 Multiwfn 自己判断
    info.update(ok=True, kind='file', reason='')
    return info


# 搜索波函数文件时跳过的重目录（避免为了找个 .fchk 去翻 node_modules）
WAVEFN_SKIP_DIRS = {'node_modules', '.git', 'dist', 'build', 'dist_electron', 'mlslib',
                    'cache', '__pycache__', '.venv', 'venv'}


def _nearby_dirs(src_dir: str, max_dirs: int = 400, max_entries: int = 20000) -> List[str]:
    """源文件所在目录的附近目录（先同级，再下一级）——log 与 fchk 常常分开放"""
    parent = os.path.dirname(os.path.abspath(src_dir))
    out, queue, seen, scanned = [], [(parent, 0)], set(), 0
    while queue and len(out) < max_dirs and scanned < max_entries:
        folder, depth = queue.pop(0)
        if folder in seen or not os.path.isdir(folder):
            continue
        seen.add(folder)
        try:
            entries = os.listdir(folder)
        except OSError:
            continue
        scanned += len(entries)
        for name in entries:
            p = os.path.join(folder, name)
            if p == os.path.abspath(src_dir) or not os.path.isdir(p):
                continue
            if name.lower() in WAVEFN_SKIP_DIRS:
                continue
            out.append(p)
            if depth < 2:
                queue.append((p, depth + 1))
    return out


def find_wavefn_companions(path: str, extra_dirs=()) -> List[str]:
    """找可替代的波函数文件

    顺序：同目录同名 → 给定目录（如目标目录）/附近子目录里的同名 → 同目录里任意波函数文件。
    只做「同名」的深层搜索，避免误用别的分子的波函数。
    """
    src_dir = os.path.dirname(os.path.abspath(path))
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    same, other = [], []

    def scan(folder: str, into_same: list, into_other: list):
        try:
            names = os.listdir(folder)
        except OSError:
            return
        for name in names:
            p = os.path.join(folder, name)
            if not os.path.isfile(p):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in WAVEFN_EXTS:
                continue
            if os.path.splitext(name)[0].lower() == stem:
                into_same.append(p)
            else:
                into_other.append(p)

    def key(p):
        e = os.path.splitext(p)[1].lower()
        return WAVEFN_PRIORITY.index(e) if e in WAVEFN_PRIORITY else 99

    dir_same, dir_other = [], []
    scan(src_dir, dir_same, dir_other)
    if dir_same:
        return sorted(dir_same, key=key) + sorted(dir_other, key=key)

    deep_same, deep_other = [], []
    for folder in list(extra_dirs or []) + _nearby_dirs(src_dir):
        scan(folder, deep_same, deep_other)
        if deep_same:
            break
    if deep_same:
        return sorted(deep_same, key=key) + sorted(deep_other, key=key)
    return sorted(dir_other, key=key)


def find_sibling_chk(path: str) -> str:
    """同名的 .chk（可交给 formchk 转成 .fchk）"""
    folder = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(folder):
        return ''
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    for name in os.listdir(folder):
        if os.path.splitext(name)[1].lower() != '.chk':
            continue
        if os.path.splitext(name)[0].lower() == stem:
            return os.path.join(folder, name)
    return ''


def find_formchk(explicit: str = '') -> str:
    """找 Gaussian 的 formchk（.chk → .fchk）"""
    if explicit and os.path.isfile(explicit):
        return explicit
    for name in FORMCHK_NAMES:
        p = shutil.which(name)
        if p:
            return p
    roots = [os.environ.get('GAUSS_EXEDIR', '')]
    for drive in ('C:', 'D:', 'E:', 'F:'):
        for name in ('G16W', 'G16', 'g16', 'G09W', 'G09', 'g09', 'Gaussian16', 'Gaussian09'):
            roots.append(os.path.join(drive + os.sep, name))
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for name in FORMCHK_NAMES:
            p = os.path.join(root, name)
            if os.path.isfile(p):
                return p
    for pat in (os.path.join('C:' + os.sep, 'G16*', 'formchk.exe'),
                os.path.join('D:' + os.sep, 'G16*', 'formchk.exe'),
                os.path.join('C:' + os.sep, 'Program Files', 'Gaussian*', 'formchk.exe')):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    return ''


def _wavefn_hint(source: str, info: dict) -> str:
    """LOG 读不到波函数时给用户的处理办法"""
    reason = info.get('reason') or '该文件里没有可用的波函数信息'
    if info.get('orca'):
        return (f'{reason}。解决办法：1) 在 ORCA 输入里加上 %output Print[P_Basis] 2 Print[P_MOs] 1 '
                f'后重新计算；2) 或直接选择 ORCA 生成的 .gbw 文件（Multiwfn 可以直接读）')
    return (f'{reason}。解决办法：1) 在 Gaussian 输入里加上 pop=full gfinput 后重新计算；'
            f'2) 或者在右上角「外部程序」旁用 formchk 把同名 .chk 转成 .fch/.fchk，再选择它；'
            f'3) 也可以直接选择已有的 .fch / .fchk / .wfn / .wfx / .molden 文件')


def _diagnose(out: str, code: int = 0, made: bool = False) -> str:
    """把 Multiwfn 的典型报错翻译成可执行的中文提示"""
    low = (out or '').lower()
    if 'no basis function information' in low:
        return ('Multiwfn 报「输入文件里没有基组信息」：请给 Gaussian 加 pop=full gfinput 后重新计算，'
                '或改用 .fchk / .wfn / .wfx / .molden 波函数文件')
    if 'no orbital' in low and ('coefficient' in low or 'information' in low):
        return ('Multiwfn 报「没有轨道系数信息」：Gaussian 输入需要加 pop=full 后重新计算，'
                '或改用 .fchk / .wfn / .wfx 波函数文件')
    if 'forrtl' in low or 'severe (' in low or 'severe(' in low:
        return ('Multiwfn 异常退出（输入脚本和程序提示对不上，常见于「按回车返回」的提示读到文件末尾）：'
                '可在「编辑脚本模板」里按你的 Multiwfn 版本调整输入脚本，或把完整日志发我')
    if 'unrecognized' in low or 'unknown format' in low or 'cannot recognize' in low or 'not a valid' in low:
        return 'Multiwfn 无法识别这个文件的格式：请改用 Gaussian/ORCA 的 .log/.out，或 .fchk/.wfn/.wfx/.molden'
    if not made and code != 0:
        return f'Multiwfn 返回码 {code} 且没有生成 cube，请看下方日志'
    return ''


def _run(cmd: List[str], cwd: str, stdin_file: str = '', timeout: int = 900, env=None):
    """跑外部程序，返回 (returncode, 输出文本)

    注意：没有输入脚本时把 stdin 接到 DEVNULL。否则子进程会继承后端（由 Electron 启动）的
    stdin 管道并一直等输入，界面就会卡在「渲染中…」。
    """
    stdin = subprocess.DEVNULL
    try:
        if stdin_file:
            stdin = open(stdin_file, 'r', encoding='utf-8', errors='replace')
        proc = subprocess.run(cmd, cwd=cwd, stdin=stdin, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout, env=env,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        out = proc.stdout.decode('utf-8', 'replace') if proc.stdout else ''
        return proc.returncode, out
    except subprocess.TimeoutExpired:
        return -1, f'超时（>{timeout}s）：{" ".join(cmd)}'
    except FileNotFoundError as e:
        return -2, f'找不到程序：{e}'
    except Exception as e:                        # noqa: BLE001
        return -3, f'调用失败：{e}'
    finally:
        if stdin_file and stdin not in (None, subprocess.DEVNULL):
            try:
                stdin.close()
            except Exception:                     # noqa: BLE001
                pass


def _tcl_path(p: str) -> str:
    """给 VMD 脚本用的路径：Tcl 会把反斜杠当转义符，必须换成正斜杠"""
    return str(p or '').replace('\\', '/')


# ===== 产物归档：<工作目录>/<分子文件名>/ 下的 分子名-xxx.cub / .png =====

def safe_name(name: str, fallback: str = 'molecule') -> str:
    """文件夹名/文件名里不能出现的字符替换掉"""
    s = re.sub(r'[\\/:*?"<>|]+', '_', str(name or '').strip())
    s = s.strip(' .')
    return s or fallback


def product_dir(work_dir: str, folder_name: str, make: bool = True) -> str:
    """产物统一放到「当前工作目录 / 该次分析命名的文件夹」里"""
    d = os.path.join(work_dir or '.', safe_name(folder_name))
    if make:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            return work_dir or '.'
    return d


def pic_dir(main_dir: str, make: bool = True) -> str:
    """图片单独放 <产物目录>/PIC —— 和 cube/脚本分开，目录不至于太乱"""
    d = os.path.join(main_dir, 'PIC')
    if make:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            return main_dir
    return d


def product_dirs(work_dir: str, folder_name: str):
    """返回 (主目录, 图片目录)"""
    main = product_dir(work_dir, folder_name)
    return main, pic_dir(main)


def move_product(path: str, dst_dir: str, new_name: str = '') -> str:
    """把产物搬进目标目录（可改名）；失败就留在原地，不影响流程"""
    if not path or not os.path.isfile(path):
        return path
    try:
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, safe_name(new_name) if new_name else os.path.basename(path))
        if os.path.abspath(dst) == os.path.abspath(path):
            return path
        os.replace(path, dst)
        return dst
    except OSError:
        return path


def annotate_png(path: str, note: str) -> bool:
    """在图片右下角写一行标注（NTO 对序号/贡献值、振子强度、Sr/D 指数等）"""
    if not note or not path or not os.path.isfile(path):
        return False
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:                              # noqa: BLE001
        return False
    try:
        with Image.open(path) as im:
            base = im.convert('RGB')
        draw = ImageDraw.Draw(base)
        size = max(14, int(base.height * 0.030))
        font = None
        for cand in (os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'msyh.ttc'),
                     os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'simhei.ttf'),
                     os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf'),
                     '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
            if os.path.isfile(cand):
                try:
                    font = ImageFont.truetype(cand, size)
                    break
                except Exception:                  # noqa: BLE001
                    font = None
        if font is None:
            font = ImageFont.load_default()
        pad = max(6, size // 3)
        try:
            box = draw.textbbox((0, 0), note, font=font)
            tw, th = box[2] - box[0], box[3] - box[1]
        except Exception:                          # noqa: BLE001
            tw, th = len(note) * size // 2, size
        x = max(0, base.width - tw - pad * 2)
        y = max(0, base.height - th - pad * 2)
        # 右下角白底 + 深色字，任何背景上都看得清
        draw.rectangle([x - pad, y - pad, base.width - 1, base.height - 1], fill=(255, 255, 255))
        draw.text((x, y), note, fill=(20, 20, 20), font=font)
        base.save(path)
        return True
    except Exception:                              # noqa: BLE001
        return False


def cleanup_scratch(folder: str):
    """删掉渲染过程产生的中转文件（_mls_*.dat/.bmp/.tga/.vmd），只留 cube 和 png"""
    for pat in ('_mls_*.dat', '_mls_*.bmp', '_mls_*.tga', '_mls_*.vmd'):
        for p in glob.glob(os.path.join(folder, pat)):
            try:
                os.remove(p)
            except OSError:
                pass


def _tail(text: str, lines: int = 40) -> str:
    rows = [r for r in (text or '').splitlines() if r.strip()]
    return '\n'.join(rows[-lines:])


def pick_companion(source: str, cands: List[str]) -> str:
    """从候选里挑「自动使用」的那个：只认同名文件

    同名（同 stem）才自动用；只是同目录里恰好有个别的波函数文件时绝不自动替换，
    否则会拿别的分子的波函数去算 —— 那种情况只作为候选列给用户点选。
    """
    stem = os.path.splitext(os.path.basename(source))[0].lower()
    for c in cands or []:
        if os.path.splitext(os.path.basename(c))[0].lower() == stem:
            return c
    return ''


def resolve_wavefn(source: str, wavefn: str = '', force: bool = False, extra_dirs=()):
    """决定 Multiwfn 实际该读哪个文件

    LOG 里没有基组/轨道系数时（Gaussian 没写 pop=full gfinput）自动改用同名的
    波函数文件（同目录、目标目录、附近子目录都会找）；实在找不到就报错并给出办法。
    返回 (文件, 提示行, 预检信息)。
    """
    src = wavefn if (wavefn and os.path.isfile(wavefn)) else source
    info = scan_source(src)
    notes = []
    if not info['ok']:
        if wavefn:
            raise HTTPException(status_code=400, detail=f'{info["reason"]}：{src}')
        pick = pick_companion(source, find_wavefn_companions(source, extra_dirs))
        if pick:
            src = pick
            info = scan_source(src)
            notes.append(f'[提示] LOG 里没有波函数信息，已自动改用同名文件：{src}')
        elif not force:
            raise HTTPException(status_code=400, detail=_wavefn_hint(source, info))
    return src, notes, info


def _expected_cubes(orb: int) -> List[str]:
    """Multiwfn 子功能 3 的产出名（实测 orb000021.cub）"""
    return [f'orb{orb:06d}.cub', f'orb{orb:05d}.cub', f'orb{orb:04d}.cub', f'orb{orb}.cub']


def _item(orb: int, cub: str, err: str) -> dict:
    return {'orbital': orb, 'ok': bool(cub), 'cub': cub,
            'name': os.path.basename(cub) if cub else '',
            'size': os.path.getsize(cub) if cub else 0, 'error': err}


def _run_multiwfn(exe: str, src: str, out_dir: str, lines: List[str],
                  in_name: str, timeout: int):
    """跑一次 Multiwfn，返回 (返回码, 输出, 本次新写/改写的 cube)"""
    in_file = os.path.join(out_dir, in_name)
    with open(in_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    before = {p: os.path.getmtime(p) for p in glob.glob(os.path.join(out_dir, '*.cub'))}
    code, out = _run([exe, src], out_dir, stdin_file=in_file, timeout=timeout)
    # 只认「本次运行新写/改写」的 cube：mtime 严格变新（不用时间窗，避免上一秒的旧 cube 被误判）
    fresh = [p for p in glob.glob(os.path.join(out_dir, '*.cub'))
             if p not in before or os.path.getmtime(p) > before[p] + 1e-6]
    return code, out, fresh


class CubRequest(BaseModel):
    source: str                                   # 波函数/日志文件（.log/.fchk/.wfn/.wfx/.molden…）
    out_dir: str
    orbitals: List[int] = []
    grid: int = 3                                 # 1 低 / 2 中 / 3 高
    multiwfn_dir: str = ''
    multiwfn_exe: str = ''
    wavefn: str = ''                              # 手动指定的波函数文件（覆盖 source）
    force: bool = False                           # 忽略「LOG 缺基组/轨道系数」预检，硬跑
    folder_name: str = ''                         # 归档子目录名（默认取 source 的文件名）
    template: Optional[List[str]] = None          # 覆盖默认输入脚本，支持 {orb} {grid}
    timeout: int = 900


@router.post("/cub")
def make_cub(req: CubRequest):
    """调用 Multiwfn 为指定轨道生成 .cub（每个轨道一次调用，便于精确定位产物）"""
    if not req.source or not os.path.isfile(req.source):
        raise HTTPException(status_code=404, detail=f'文件不存在: {req.source}')
    if not req.orbitals:
        raise HTTPException(status_code=400, detail='请先选择轨道')
    out_dir = req.out_dir or os.path.dirname(req.source)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f'无法创建目录: {e}')
    exe = req.multiwfn_exe or find_program(req.multiwfn_dir, 'multiwfn')
    if not exe or not os.path.isfile(exe):
        raise HTTPException(status_code=400, detail='没找到 Multiwfn 可执行文件，请先在右上角「外部程序」里配置目录')

    # ===== 波函数来源：LOG 没有基组/轨道系数时，自动换用同名波函数文件 =====
    src, notes, info = resolve_wavefn(req.source, req.wavefn, req.force, [out_dir])
    notes.append(f'[提示] 波函数来源：{src}')

    tpl = req.template or plot_config.multiwfn_template()      # 默认脚本可在 mls-plots.json 里改
    orbs = sorted({int(o) for o in req.orbitals if int(o) > 0})[:64]

    def script_of(orb_text: str) -> List[str]:
        lines = [str(l).replace('{orb}', orb_text).replace('{grid}', str(req.grid)) for l in tpl]
        return lines + [l for l in MWFN_TAIL if l not in lines]

    logs, items, todo = [], [], []
    # 一次调用把所有轨道一起生成（Multiwfn 支持 "1,3-6,8" 写法，省去反复加载波函数）
    joined = ','.join(str(o) for o in orbs)
    code, out, fresh = _run_multiwfn(exe, src, out_dir, script_of(joined),
                                     '_mls_multiwfn_orb.txt', req.timeout)
    by_name = {os.path.basename(p).lower(): p for p in fresh}
    for orb in orbs:
        cub = next((by_name[n.lower()] for n in _expected_cubes(orb) if n.lower() in by_name), '')
        if cub:
            items.append(_item(orb, cub, ''))
        else:
            todo.append(orb)
    if items:
        logs.append(f'--- Multiwfn 一次生成 {len(orbs)} 个轨道（返回码 {code}）：拿到 {len(items)} 个 cube ---')
        if todo:
            logs.append(f'[提示] 轨道 {",".join(str(o) for o in todo)} 没有对应 cube，改为逐个重新生成')
    else:
        logs.append(f'--- Multiwfn 生成轨道 {joined}（返回码 {code}）---\n{_tail(out, 20)}')
    # 兜底：逐个轨道单独调用（不同版本的命名 / 菜单流程可能不一样）
    for orb in todo:
        code2, out2, fresh2 = _run_multiwfn(exe, src, out_dir, script_of(str(orb)),
                                            f'_mls_multiwfn_orb{orb}.txt', req.timeout)
        cub = next((p for p in fresh2
                    if os.path.basename(p).lower() in [n.lower() for n in _expected_cubes(orb)]), '')
        if not cub and len(fresh2) == 1:
            cub = fresh2[0]                       # 名字对不上也无妨：这次只新出了这一个 cube
        items.append(_item(orb, cub, '' if cub else _diagnose(out2, code2, False)))
        if cub:
            logs.append(f'--- Multiwfn 轨道 {orb}（返回码 {code2}）→ {os.path.basename(cub)} ---')
        else:
            logs.append(f'--- Multiwfn 轨道 {orb} 失败（返回码 {code2}）---\n{_tail(out2, 20)}')
    items.sort(key=lambda i: i['orbital'])
    # 产物归档：<工作目录>/<分子名>-Orbitals/分子名-orb<序号>.cub（图片另外进 PIC/）
    base = safe_name(req.folder_name or os.path.splitext(os.path.basename(req.source))[0])
    pdir = product_dir(out_dir, base + SUFFIX_ORBITALS)
    for it in items:
        if it['cub']:
            newp = move_product(it['cub'], pdir, f'{base}-orb{it["orbital"]}.cub')
            it['cub'] = newp
            it['name'] = os.path.basename(newp)
            it['size'] = os.path.getsize(newp) if os.path.isfile(newp) else 0
    hint = ''
    if items and not any(i['ok'] for i in items):
        hint = next((i['error'] for i in items if i['error']), '') \
            or 'Multiwfn 没有生成任何 cube，请看下方日志'
    return {'ok': all(i['ok'] for i in items), 'out_dir': pdir, 'items': items,
            'log': '\n'.join(notes + logs), 'hint': hint, 'source': src}


@router.get("/wavefn")
async def wavefn_info(path: str = '', dir: str = ''):
    """预检：这个文件能不能被 Multiwfn 读成波函数？同目录/附近有没有可替代的波函数文件？"""
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f'文件不存在: {path}')
    info = scan_source(path)
    friends = find_wavefn_companions(path, [dir] if dir else [])
    chk = find_sibling_chk(path)
    pick = pick_companion(path, friends)
    return {**info, 'name': os.path.basename(path),
            'companions': friends, 'picked': pick,
            'chk': chk, 'formchk': find_formchk(),
            'hint': '' if info['ok'] else _wavefn_hint(path, info)}


class FormchkRequest(BaseModel):
    chk: str
    out_dir: str = ''
    formchk_exe: str = ''
    timeout: int = 600


@router.post("/formchk")
def run_formchk(req: FormchkRequest):
    """用 Gaussian 的 formchk 把 .chk 转成 Multiwfn 能读的 .fchk"""
    if not req.chk or not os.path.isfile(req.chk):
        raise HTTPException(status_code=404, detail=f'文件不存在: {req.chk}')
    exe = find_formchk(req.formchk_exe)
    if not exe:
        raise HTTPException(status_code=400,
                            detail='没找到 Gaussian 的 formchk.exe：请把它所在目录加入 PATH，或手工转换后选择 .fchk')
    out_dir = req.out_dir or os.path.dirname(os.path.abspath(req.chk))
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(req.chk))[0] + '.fchk')
    code, log = _run([exe, req.chk, out], out_dir, timeout=req.timeout)
    ok = os.path.isfile(out) and os.path.getsize(out) > 0
    return {'ok': ok, 'fchk': out if ok else '', 'code': code, 'exe': exe,
            'log': _tail(log, 20),
            'error': '' if ok else (_tail(log, 6) or 'formchk 没有生成 .fchk')}


class RenderRequest(BaseModel):
    out_dir: str
    items: List[dict] = []                        # [{orbital, cub, note?}]
    vmd_dir: str = ''
    vmd_exe: str = ''
    folder_name: str = ''                         # 归档子目录名（默认取 cube 所在目录名）
    size: List[int] = []                          # 空 = 用所选风格的默认分辨率
    iso: float = 0.05                             # 等值面数值（正负各画一张）
    style: str = 'art_noshadow'                   # art_noshadow（默认，无阴影）| art（带阴影）| standard
    trans_mode: str = ''                          # 覆盖 tachyon 的透明选项：vmd / raster3d / trans_vmd
    script: Optional[List[str]] = None            # 覆盖默认 VMD 脚本，支持 {cub} {scene} {w} {h} {iso}
    use_tachyon: bool = True
    tachyon: Optional[List[str]] = None           # 覆盖默认 tachyon 参数
    timeout: int = 1800


def _bmp_or_tga_to_png(path: str, png: str) -> bool:
    """用 Pillow 把 tachyon 出的 BMP/TGA 转成 PNG（界面/报告都更好用）"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.save(png)
        return os.path.exists(png)
    except Exception:                             # noqa: BLE001
        return False


def _vmd_proc(tpl: List[str]) -> List[str]:
    """把 VMD 模板包成一个 proc：模板里的 {cub}/{scene}/{w}/{h}/{iso}/{png}/{bmp}/{tga} → Tcl 变量

    这样一次 VMD 启动就能渲染全部轨道（VMD 冷启动很慢）；模板里直接写 $cub 也照样能用。
    """
    body = []
    for line in tpl:
        s = str(line)
        for key in ('cub', 'scene', 'w', 'h', 'iso', 'png', 'bmp', 'tga'):
            s = s.replace('{' + key + '}', '$' + key)
        body.append('  ' + s)
    return ['proc mls_orb {cub scene w h iso png bmp tga} {'] + body + ['}']


def _render_one(exe: str, script_path: str, out_dir: str, timeout: int):
    # -eofexit 只在 stdin 结束时才退出，VMD 1.9.3 实测仍会停在控制台；
    # 真正可靠的是脚本最后一句 quit（由调用方追加）。
    return _run([exe, '-dispdev', 'text', '-e', script_path, '-eofexit'], out_dir, timeout=timeout)


@router.post("/render")
def render_orbitals(req: RenderRequest):
    """调用 VMD（必要时再用 tachyon）把 cube 渲染成图片；图片统一进 cube 所在产物目录的 PIC/"""
    items = [it for it in req.items if it.get('cub') and os.path.isfile(it['cub'])]
    if not items:
        raise HTTPException(status_code=400, detail='没有可渲染的 .cub 文件，请先生成 cub')
    out_dir = req.out_dir or os.path.dirname(items[0]['cub'])
    exe = req.vmd_exe or find_program(req.vmd_dir, 'vmd')
    if not exe or not os.path.isfile(exe):
        raise HTTPException(status_code=400, detail='没找到 VMD 可执行文件，请先在右上角「外部程序」里配置目录')
    vmd_dir = os.path.dirname(exe)
    tachyon_exe = ''
    if req.use_tachyon:
        for name in ('tachyon_WIN32.exe', 'tachyon.exe', 'tachyon_WIN64.exe', 'tachyon'):
            p = os.path.join(vmd_dir, name)
            if os.path.isfile(p):
                tachyon_exe = p
                break
        if not tachyon_exe:
            tachyon_exe = find_in_path('tachyon')      # VMD 的 tachyon 常常也在 PATH 里
    styles = plot_config.vmd_styles()               # 风格来自 mls-plots.json（可改）
    base_tpl = plot_config.vmd_template()
    # 没指定 / 指定了不存在的风格 → 用配置里的默认风格（默认 art_noshadow，无阴影）
    sel = (styles.get(req.style) or styles.get(plot_config.default_style())
           or styles.get('standard') or ([], plot_config.DEFAULT_TACHYON, [1600, 1200]))
    w, h = (req.size or list(sel[2]) + [1600, 1200])[:2]
    iso = req.iso
    style_lines, style_tachyon, _size = sel
    if req.script:
        tpl = req.script
    elif style_lines:
        # 艺术级设定要放在建好表示（rep）之后、渲染之前
        tpl = list(base_tpl)
        cut = len(tpl) - 1 if str(tpl[-1]).strip().startswith('render ') else len(tpl)
        tpl = tpl[:cut] + list(style_lines) + tpl[cut:]
    else:
        tpl = base_tpl
    tpl_t = req.tachyon or plot_config.apply_trans_mode(style_tachyon, req.trans_mode)
    logs = []

    # 图片统一放进「cube 所在产物目录」的 PIC/ 子目录（cube 与图分开，目录不乱）
    folder = req.folder_name
    if not folder:
        cub_dir = os.path.dirname(os.path.abspath(items[0]['cub']))
        work = os.path.abspath(out_dir)
        folder = os.path.basename(cub_dir) if cub_dir != work else os.path.basename(work)
    main_dir = product_dir(out_dir, folder)
    pdir = pic_dir(main_dir)
    jobs = []
    for it in items[:64]:
        orb = int(it.get('orbital', 0))
        cub = it['cub']
        stem = os.path.splitext(os.path.basename(cub))[0]
        jobs.append({'orbital': orb, 'cub': cub, 'stem': stem, 'note': it.get('note') or '',
                     'scene': os.path.join(pdir, f'_mls_{stem}.dat'),
                     'png': os.path.join(pdir, f'{stem}.png'),
                     'bmp': os.path.join(pdir, f'_mls_{stem}.bmp'),
                     'tga': os.path.join(pdir, f'_mls_{stem}.tga')})

    # 一次 VMD 启动渲染所有轨道（模板包成 proc，逐个调用）
    if not tachyon_exe:
        # 没有外部 tachyon：改用 VMD 内置渲染器，直接出 TGA
        tpl = [str(ln).replace('render Tachyon {scene}', 'render TachyonInternal {tga}') for ln in tpl]
    lines = _vmd_proc(tpl)
    for j in jobs:
        # 交给 VMD 的文件名用「相对文件名」：VMD 调外部 Tachyon 时会把
        # "render Tachyon <路径>" 当命令行执行，路径里有空格就断了（cwd 已经是 out_dir）
        lines.append('mls_orb {{{0}}} {1} {2} {3} {4} {5} {6} {7}'.format(
            _tcl_path(j['cub']), os.path.basename(j['scene']), w, h, iso,
            os.path.basename(j['png']), os.path.basename(j['bmp']), os.path.basename(j['tga'])))
    lines.append('quit')
    script_path = os.path.join(pdir, '_mls_orbitals.vmd')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    code, out = _render_one(exe, script_path, pdir, req.timeout)
    logs.append(f'--- VMD 渲染 {len(jobs)} 个轨道（返回码 {code}）---\n{_tail(out, 12)}')

    made_scenes = [j for j in jobs if os.path.isfile(j['scene'])]
    if not made_scenes:
        # 兜底：模板可能不适合包成 proc，退回「每个轨道单独一个脚本 + 单独启动 VMD」
        logs.append('[提示] 批量渲染没有产生场景文件，改为逐个轨道单独调用 VMD')
        for j in jobs:
            one = []
            for line in tpl:
                one.append(str(line).replace('{cub}', _tcl_path(j['cub']))
                           .replace('{scene}', os.path.basename(j['scene']))
                           .replace('{w}', str(w)).replace('{h}', str(h))
                           .replace('{iso}', str(iso))
                           .replace('{png}', os.path.basename(j['png']))
                           .replace('{bmp}', os.path.basename(j['bmp']))
                           .replace('{tga}', os.path.basename(j['tga'])))
            one.append('quit')
            p = os.path.join(pdir, f'_mls_{j["stem"]}.vmd')
            with open(p, 'w', encoding='utf-8') as f:
                f.write('\n'.join(one) + '\n')
            c2, o2 = _render_one(exe, p, pdir, req.timeout)
            logs.append(f'--- VMD {j["stem"]}（返回码 {c2}）---\n{_tail(o2, 6)}')

    results = []
    for j in jobs:
        made = ''
        if tachyon_exe and os.path.isfile(j['scene']):
            # tachyon_WIN32 处理不了带空格的绝对路径（会静默不写文件），一律用相对文件名
            # （_run 的 cwd 已经是产物目录，所以相对名就落在那里）
            args = [tachyon_exe] + [str(a).replace('{scene}', os.path.basename(j['scene']))
                                    .replace('{bmp}', os.path.basename(j['bmp']))
                                    .replace('{w}', str(w)).replace('{h}', str(h))
                                    for a in tpl_t]
            logs.append(f'--- tachyon 参数：{" ".join(str(a) for a in args[1:])} ---')
            code2, out2 = _run(args, pdir, timeout=req.timeout)
            logs.append(f'--- tachyon {j["stem"]}（返回码 {code2}）---\n{_tail(out2, 6)}')
            if os.path.isfile(j['bmp']) and _bmp_or_tga_to_png(j['bmp'], j['png']):
                made = j['png']
        if not made and os.path.isfile(j['tga']) and _bmp_or_tga_to_png(j['tga'], j['png']):
            made = j['png']
        if not made and os.path.isfile(j['png']):
            made = j['png']
        if made and j['note']:
            annotate_png(made, j['note'])           # 右下角标注（NTO 对/贡献值/振子强度等）
        results.append({'orbital': j['orbital'], 'ok': bool(made), 'image': made,
                        'cub': j['cub'], 'name': os.path.basename(made) if made else '',
                        'note': j['note']})
    if all(r['ok'] for r in results):
        cleanup_scratch(pdir)
    return {'ok': all(r['ok'] for r in results), 'out_dir': pdir,
            'items': results, 'log': '\n'.join(logs)}


class ReadCubRequest(BaseModel):
    path: str
    max_bytes: int = 40 * 1024 * 1024


@router.post("/read-cub")
async def read_cub(req: ReadCubRequest):
    """把 .cub 文本交给前端做等值面预览（3Dmol 支持 cube 体数据）"""
    if not req.path or not os.path.isfile(req.path):
        raise HTTPException(status_code=404, detail=f'文件不存在: {req.path}')
    size = os.path.getsize(req.path)
    if size > req.max_bytes:
        raise HTTPException(status_code=400, detail=f'cube 文件过大（{size // 1024 // 1024} MB），请提高网格精度或换小分子')
    with open(req.path, 'r', encoding='utf-8', errors='replace') as f:
        return {'path': req.path, 'size': size, 'text': f.read()}


class ReadImageRequest(BaseModel):
    path: str
    max_bytes: int = 40 * 1024 * 1024
    max_w: int = 0                    # >0 时按最大宽度缩放（界面缩略图用，恢复缓存快很多）


def _thumb_cache_dir() -> str:
    """缩略图缓存目录：优先用户缓存目录，不可写就退到临时目录；都不可写返回空串"""
    env = os.environ.get('MLS_THUMB_DIR')
    cands = [env] if env else []
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('XDG_CACHE_HOME')
    if base:
        cands.append(os.path.join(base, 'mls-desktop', 'thumbs'))
    cands.append(os.path.join(tempfile.gettempdir(), 'mls-desktop-thumbs'))
    for d in cands:
        if not d:
            continue
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except OSError:
            continue
    return ''


def make_thumb(path: str, max_w: int) -> str:
    """生成/复用缩略图（按 路径+修改时间+宽度 缓存）；失败就返回原图路径"""
    if max_w <= 0:
        return path
    cache_dir = _thumb_cache_dir()
    if not cache_dir:
        return path
    try:
        from PIL import Image
    except Exception:                              # noqa: BLE001
        return path
    try:
        key = hashlib.sha1(f'{os.path.abspath(path)}|{os.path.getmtime(path)}|{max_w}'
                           .encode('utf-8')).hexdigest()
        out = os.path.join(cache_dir, key + '.png')
        if os.path.isfile(out) and os.path.getmtime(out) >= os.path.getmtime(path):
            return out
        with Image.open(path) as im:
            if im.width <= max_w:
                return path
            h = max(1, int(round(im.height * max_w / float(im.width))))
            im.convert('RGB').resize((max_w, h), Image.LANCZOS).save(out, 'PNG', optimize=True)
        return out
    except Exception:                              # noqa: BLE001
        return path


@router.post("/read-image")
def read_image(req: ReadImageRequest):
    """把渲染出的图片读成 base64（避免前端受 file:// 同源策略限制）

    max_w > 0 时先缩成缩略图再返回：界面上的图都很小，缩略图体积只有原图的几十分之一，
    切回之前解析过的文件时不用再解码整张大图，恢复瞬间就出来了（点开大图时才读原图）。
    """
    import base64
    import mimetypes
    if not req.path or not os.path.isfile(req.path):
        raise HTTPException(status_code=404, detail=f'文件不存在: {req.path}')
    src = make_thumb(req.path, req.max_w)
    size = os.path.getsize(src)
    if size > req.max_bytes:
        raise HTTPException(status_code=400, detail=f'图片过大（{size // 1024} KB）')
    mime = mimetypes.guess_type(src)[0] or 'image/png'
    with open(src, 'rb') as f:
        blob = base64.b64encode(f.read()).decode('ascii')
    return {'path': req.path, 'size': size, 'mime': mime, 'base64': blob,
            'thumb': src != req.path}


@router.get("/program")
async def which_program(kind: str = 'multiwfn', dir: str = ''):
    """查外部程序可执行文件路径"""
    p = find_program(dir, kind)
    return {'kind': kind, 'dir': dir, 'path': p, 'ok': bool(p)}


@router.get("/defaults")
def defaults():
    """默认脚本模板（前端可编辑）+ 配置文件位置（用户可直接改 json）"""
    cfg = plot_config.load_config()
    return {'multiwfn': plot_config.multiwfn_template(), 'vmd': plot_config.vmd_template(),
            'tachyon': plot_config.DEFAULT_TACHYON,
            'vmd_art': (cfg.get('styles', {}).get('art', {}) or {}).get('vmd', plot_config.ART_VMD),
            'tachyon_art': (cfg.get('styles', {}).get('art', {}) or {}).get('tachyon', plot_config.ART_TACHYON),
            'tachyon_art_noshadow': (cfg.get('styles', {}).get('art_noshadow', {}) or {}).get('tachyon', plot_config.ART_TACHYON_NOSHADOW),
            'tail': MWFN_TAIL,
            'hole_electron': plot_config.hole_electron_defaults(),
            'style': plot_config.default_style(),
            'config_path': plot_config.config_path(),
            'config': cfg}


@router.get("/citation")
async def citation(kind: str = '', dir: str = ''):
    """Multiwfn 引用说明（每次调用 Multiwfn 功能前，界面必须整屏展示并让用户确认）"""
    exe = find_program(dir, 'multiwfn')
    return citation_payload(kind=kind, multiwfn_exe=exe)
