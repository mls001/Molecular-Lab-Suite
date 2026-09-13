"""绘图配置：软件根目录下的 mls-plots.json

所有绘图风格（VMD 脚本、Tachyon 参数、分辨率）与脚本模板都集中在这里，
后端每次请求时读取一次（按修改时间缓存），用户可以直接改这个文件而不必改代码。

文件不存在时会自动写出一份默认配置，方便用户照着改。
"""
import json
import os
from typing import List

CONFIG_NAME = 'mls-plots.json'

# ===== 内置默认值（写进 json 的初始内容；json 里改了就以后者为准）=====
DEFAULT_VMD_TEMPLATE = [
    'mol delete all',
    'mol new {cub} type cube',
    'mol modstyle 0 top CPK 0.800000 0.300000 22.000000 22.000000',
    'mol addrep top',
    'mol modstyle 1 top Isosurface {iso} 0 0 0 1 1',
    'mol modcolor 1 top ColorID 1',
    'mol modmaterial 1 top Glossy',
    'mol addrep top',
    'mol modstyle 2 top Isosurface -{iso} 0 0 0 1 1',
    'mol modcolor 2 top ColorID 0',
    'mol modmaterial 2 top Glossy',
    'color Display Background white',
    'display depthcue off',
    'axes location Off',
    'display resize {w} {h}',
    'render Tachyon {scene}',
]

DEFAULT_TACHYON = ['{scene}', '-format', 'BMP', '-o', '{bmp}', '-trans_raster3d',
                   '-res', '{w}', '{h}', '-numthreads', '4', '-aasamples', '24', '-mediumshade']

# 艺术级（sobereva.com/449，取自 Multiwfn 作者的 VMDrender.txt）
ART_VMD = [
    'color Name C tan',
    'color change rgb tan 0.700000 0.560000 0.360000',
    'material change mirror Opaque 0.15',
    'material change outline Opaque 4.000000',
    'material change outlinewidth Opaque 0.5',
    'material change ambient Glossy 0.1',
    'material change diffuse Glossy 0.600000',
    'material change opacity Glossy 0.75',
    'material change ambient Opaque 0.08',
    'material change mirror Opaque 0.0',
    'material change shininess Glossy 1.0',
    'mol modcolor 1 top ColorID 12',
    'mol modcolor 2 top ColorID 22',
    'display distance -7.0',
    'display height 10',
    'light 3 on',
]
ART_TACHYON = ['{scene}', '-format', 'BMP', '-o', '{bmp}', '-trans_raster3d',
               '-res', '{w}', '{h}', '-fullshade', '-numthreads', '4', '-aasamples', '24']
ART_TACHYON_NOSHADOW = ['{scene}', '-format', 'BMP', '-o', '{bmp}', '-trans_raster3d',
                        '-res', '{w}', '{h}', '-mediumshade', '-numthreads', '4', '-aasamples', '24']

DEFAULT_OVERLAY_PROC = """proc mls_overlay {cub1 cub2 scene w h iso transparent spheres material} {
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
  # Translucent：密度等值面用（低环境光、无高光，避免过曝又能看见内部质心）
  material change ambient Translucent 0.05
  material change diffuse Translucent 0.35
  material change specular Translucent 0.0
  material change shininess Translucent 0.0
  material change opacity Translucent 0.25
  if {$material eq "Glossy"} { light 3 on }
  if {$cub1 ne ""} {
    mol new $cub1 type cube
    mol modstyle 0 top CPK 0.800000 0.300000 22.000000 22.000000
    mol addrep top
    mol modstyle 1 top Isosurface $iso 0 0 0 1 1
    mol modcolor 1 top ColorID 12
    mol modmaterial 1 top $material
  }
  if {$cub2 ne ""} {
    mol new $cub2 type cube
    mol modstyle 0 top CPK 0.800000 0.300000 22.000000 22.000000
    mol addrep top
    mol modstyle 1 top Isosurface $iso 0 0 0 1 1
    mol modcolor 1 top ColorID 22
    mol modmaterial 1 top $material
  }
  if {$transparent} {
    set op {opacity_single}
    if {$cub2 ne ""} { set op {opacity_two} }
    material change opacity $material $op
    material change ambient $material 0.04
  }
  foreach s $spheres {
    draw color [lindex $s 3]
    draw sphere [list [lindex $s 0] [lindex $s 1] [lindex $s 2]] radius {sphere_radius} resolution 24
  }
  display distance -7.0
  display height 10
  display resize $w $h
  render Tachyon $scene
}
"""

DEFAULT_MWFN_TEMPLATE = ['200', '3', '{orb}', '{grid}', '1']

DEFAULTS = {
    '_说明': 'MLS 绘图配置：改这里就能改绘图风格/脚本/参数，保存后下次绘制生效（不用改代码）',
    'default_style': 'art_noshadow',
    'styles': {
        'standard': {'vmd': [], 'tachyon': DEFAULT_TACHYON, 'size': [1600, 1200]},
        'art': {'vmd': ART_VMD, 'tachyon': ART_TACHYON, 'size': [1400, 1050]},
        'art_noshadow': {'vmd': ART_VMD, 'tachyon': ART_TACHYON_NOSHADOW, 'size': [1400, 1050]},
    },
    'vmd_template': DEFAULT_VMD_TEMPLATE,
    'overlay_proc': DEFAULT_OVERLAY_PROC,
    'multiwfn_template': DEFAULT_MWFN_TEMPLATE,
    'hole_electron': {
        'iso': 0.0005,
        'material': 'Translucent',
        'trans_mode': 'trans_vmd',
        'sphere_radius': 0.35,
        'opacity_single': 0.3,
        'opacity_two': 0.3,
    },
}

_cache = {'path': '', 'mtime': None, 'data': None}


def app_dir() -> str:
    """软件根目录（打包后就是 .exe 所在目录；开发时是仓库根目录）"""
    d = os.environ.get('MLS_APP_DIR')
    if d and os.path.isdir(d):
        return d
    mols = os.environ.get('MLS_MOLS_DIR')
    if mols:
        return os.path.dirname(os.path.abspath(mols))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def config_path() -> str:
    return os.path.join(app_dir(), CONFIG_NAME)


def _write_defaults(path: str):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULTS, f, ensure_ascii=False, indent=2)
            f.write('\n')
    except OSError:
        pass


def load_config() -> dict:
    """读配置：文件不存在就写一份默认的；解析失败就退回内置默认值"""
    path = config_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    if _cache['data'] is not None and _cache['path'] == path and _cache['mtime'] == mtime:
        return _cache['data']

    if mtime is None:
        _write_defaults(path)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None

    data = json.loads(json.dumps(DEFAULTS))          # 深拷贝默认值
    if mtime is not None:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                user = json.load(f)
            if isinstance(user, dict):
                data.update(user)                    # 顶层键覆盖
        except (OSError, ValueError):
            pass
    _cache.update({'path': path, 'mtime': mtime, 'data': data})
    return data


def apply_trans_mode(args: List[str], mode: str) -> List[str]:
    """把 tachyon 参数里的 -trans_xxx 换成用户要的透明模式

    mode 可以写 'vmd' / 'raster3d' / 'trans_vmd' / '-trans_vmd'（都认）；
    args 里本来没有透明选项时就补一个，保证切换真的生效。
    """
    m = str(mode or '').strip().lower()
    if m.startswith('-'):
        m = m[1:]
    if m.startswith('trans_'):
        m = m[len('trans_'):]
    if m not in ('raster3d', 'vmd', 'vmd_nosort'):
        return list(args)
    flag = '-trans_' + m
    out = list(args)
    if any(str(a).startswith('-trans_') for a in out):
        return [flag if str(a).startswith('-trans_') else a for a in out]
    return out + [flag]


def vmd_styles() -> dict:
    """{style: (vmd 附加设定, tachyon 参数, 默认分辨率)}"""
    cfg = load_config()
    out = {}
    for name, v in (cfg.get('styles') or {}).items():
        if not isinstance(v, dict):
            continue
        out[name] = (list(v.get('vmd') or []),
                     list(v.get('tachyon') or DEFAULT_TACHYON),
                     list(v.get('size') or [1600, 1200]))
    return out or {'standard': ([], DEFAULT_TACHYON, [1600, 1200])}


def default_style() -> str:
    """界面默认用哪种渲染风格（默认 art_noshadow：无阴影，快且干净）"""
    cfg = load_config()
    s = cfg.get('default_style')
    if isinstance(s, str) and s in vmd_styles():
        return s
    return 'art_noshadow'


def vmd_template() -> List[str]:
    cfg = load_config()
    tpl = cfg.get('vmd_template')
    return list(tpl) if isinstance(tpl, list) and tpl else DEFAULT_VMD_TEMPLATE


def overlay_proc() -> str:
    """叠加图脚本：把 {sphere_radius}/{opacity_single}/{opacity_two} 填进去"""
    cfg = load_config()
    proc = cfg.get('overlay_proc')
    he = cfg.get('hole_electron') or {}
    if not isinstance(proc, str) or 'proc mls_overlay' not in proc:
        proc = DEFAULT_OVERLAY_PROC
    return (proc.replace('{sphere_radius}', str(he.get('sphere_radius', 0.35)))
                .replace('{opacity_single}', str(he.get('opacity_single', 0.22)))
                .replace('{opacity_two}', str(he.get('opacity_two', 0.10))))


def multiwfn_template() -> List[str]:
    cfg = load_config()
    tpl = cfg.get('multiwfn_template')
    return list(tpl) if isinstance(tpl, list) and tpl else DEFAULT_MWFN_TEMPLATE


def hole_electron_defaults() -> dict:
    cfg = load_config()
    he = cfg.get('hole_electron') or {}
    d = dict(DEFAULTS['hole_electron'])
    if isinstance(he, dict):
        d.update(he)
    return d
