// 2D 结构式渲染的共用纯函数（画布组件与离线预览工具共用，避免渲染逻辑重复）
// 坐标一律用屏幕像素；分子坐标 → 像素的换算由调用方负责。

export const CPK = {
  H: '#404040', C: '#000000', N: '#3050f8', O: '#e60000', S: '#b8860b',
  F: '#59a83b', Cl: '#1f9e1f', Br: '#a62929', I: '#8b2fa0', P: '#e07b00',
  B: '#c07a5a', Si: '#8a7a5a', Se: '#a0522d', Na: '#8b5cf6', K: '#8b5cf6',
  Mg: '#3a9e3a', Ca: '#3a9e3a', Fe: '#c05a2a', Co: '#c05a2a', Ni: '#3a9e6a',
  Cu: '#b87333', Zn: '#7a8a9a', Ru: '#8a4a7a', Rh: '#8a4a7a', Pd: '#6a6a9a',
  Ag: '#8a8a9a', Ir: '#7a4a8a', Pt: '#6a8a9a', Au: '#b8960b', Hg: '#8a8a9a'
}

export const BOND_COLOR = '#111111'

// 3D 用配色：碳用中灰、氢用近白（否则深色背景下黑碳会让整个模型看起来很黑）
export const CPK3D = Object.assign({}, CPK, { C: '#a6a6a6', H: '#f2f2f2' })

// 深色画布（暗色主题）下的配套颜色：键变浅、元素色提亮，保证对比度
export function bondColorFor(dark) {
  return dark ? '#e9ecef' : BOND_COLOR
}
export function lighten(hex, k = 0.4) {
  if (!hex || hex.charAt(0) !== '#') return hex
  const h = hex.slice(1)
  const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h
  const r = parseInt(n.slice(0, 2), 16)
  const g = parseInt(n.slice(2, 4), 16)
  const b = parseInt(n.slice(4, 6), 16)
  const mix = (v) => Math.round(v + (255 - v) * k)
  return '#' + [mix(r), mix(g), mix(b)].map(v => v.toString(16).padStart(2, '0')).join('')
}
export function isDarkColor(hex) {
  const h = (hex || '').replace('#', '')
  if (h.length < 6) return false
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return (0.299 * r + 0.587 * g + 0.114 * b) < 140
}

// 标准键长 1.4 Å → 字号约为键长的 0.42（和 ChemDraw/MolView 的比例一致）
export function fontSizeFor(bondPx) {
  return Math.max(11, Math.min(20, bondPx * 0.42))
}

// 双键两条线的间距
export function bondGapFor(bondPx) {
  return Math.max(2.2, Math.min(5, bondPx * 0.11))
}

// 原子文字：骨架式下碳不标；非骨架式（showExplicitCH）碳也标出 CH3/CH2…
// 孤立的碳原子（没有任何重原子邻居，如刚画下的第一个原子）始终显示 CH4/CH3，否则它在骨架式里会看不见
export function atomText(atom, { showExplicitCH = false, dark = false } = {}) {
  if (atom.is_h) return { label: 'H', sub: '', charge: '', color: dark ? lighten(CPK.H, 0.5) : CPK.H }
  const nH = atom.n_h || 0
  const isolated = (atom.heavy_degree || 0) === 0
  let label = atom.symbol
  if (atom.symbol === 'C') {
    if (!atom.charge && !showExplicitCH && !isolated) label = ''
    else if (nH > 0) label = 'CH'
  } else if (nH >= 1) {
    label = atom.symbol + 'H'
  }
  const c = atom.charge || 0
  const charge = c === 0 ? '' : (c === 1 ? '+' : (c === -1 ? '–' : (c > 0 ? c + '+' : Math.abs(c) + '–')))
  const base = CPK[atom.symbol] || '#000000'
  return {
    label,
    sub: (nH > 1 && label.endsWith('H')) ? String(nH) : '',
    charge,
    color: dark ? lighten(base, base === CPK.C ? 0.85 : 0.35) : base
  }
}

// 键的线段：单键 1 条、双键 2 条、三键 3 条；
// 芳香键按后端给的 display_order（Kekulé）画，环内双键的第二条线画在环内侧并缩短。
export function bondSegments(bond, pa, pb, { gapA = 0, gapB = 0, bondGap = 3.2, bondPx = 60 } = {}) {
  const dx = pb.X - pa.X
  const dy = pb.Y - pa.Y
  const L = Math.hypot(dx, dy) || 1
  const ux = dx / L, uy = dy / L
  const nx = -uy, ny = ux
  const p1 = { x: pa.X + ux * gapA, y: pa.Y + uy * gapA }
  const p2 = { x: pb.X - ux * gapB, y: pb.Y - uy * gapB }
  const seg = (o, trim = 0) => ({
    x1: p1.x + nx * o + ux * trim, y1: p1.y + ny * o + uy * trim,
    x2: p2.x + nx * o - ux * trim, y2: p2.y + ny * o - uy * trim
  })
  const order = bond.display_order || Math.round(bond.order) || 1
  if (order <= 1) return [seg(0)]
  if (order === 2) {
    if (bond.in_ring) {
      // 环内双键：一条在键轴上、一条在环内侧（两端缩进，符合 ChemDraw 画法）
      const side = bond.flip ? -1 : 1
      return [seg(0), seg(side * bondGap, Math.min(L * 0.16, bondGap * 2.2))]
    }
    return [seg(-bondGap / 2), seg(bondGap / 2)]
  }
  const trim = bond.in_ring ? Math.min(L * 0.16, bondGap * 2.2) : 0
  return [seg(0), seg(-bondGap, trim), seg(bondGap, trim)]
}

const BOND = 1.4                                  // 标准键长（Å）

// 单击原子「自动接键」时新原子的落点：躲开已有键的方向，按标准键长放一个原子
// 只有一个键时按 60° 转向（碳链因此是标准锯齿形，而不是一直拉直/直角）；
// 两个以上键时取已有键方向的合力反方向（等价于 120° 的四面体投影）
export function freeBondPosition(atoms, bonds, index) {
  const self = atoms.find(a => a.index === index)
  if (!self) return null
  const dir = Math.PI / 6                                // 30°：链的起始方向
  const nbrs = []
  for (const b of bonds) {
    const other = b.a === index ? b.b : (b.b === index ? b.a : null)
    if (other === null) continue
    const a = atoms.find(x => x.index === other)
    if (a) nbrs.push({ x: a.x - self.x, y: a.y - self.y })
  }
  const place = (ang) => ({ x: self.x + Math.cos(ang) * BOND, y: self.y + Math.sin(ang) * BOND })
  if (!nbrs.length) return place(dir)
  let sx = 0, sy = 0
  for (const v of nbrs) {
    const L = Math.hypot(v.x, v.y) || 1
    sx += v.x / L
    sy += v.y / L
  }
  if (nbrs.length === 1) {
    // 键链：来向 θ（上一条键的前进方向），新键取 θ ± 60°（向上来的往下拐、向下/水平的往上拐）→ 锯齿形
    const theta = Math.atan2(-nbrs[0].y, -nbrs[0].x)
    const turn = (-nbrs[0].y) > 1e-6 ? -Math.PI / 3 : Math.PI / 3
    return place(theta + turn)
  }
  let dx = -sx, dy = -sy
  if (Math.hypot(dx, dy) < 1e-3) {
    // 已有键方向正好互相抵消（如对位两条）：取第一条键逆时针 90°
    const v = nbrs[0]
    const L = Math.hypot(v.x, v.y) || 1
    dx = -v.y / L
    dy = v.x / L
  }
  const L = Math.hypot(dx, dy) || 1
  return { x: self.x + dx / L * BOND, y: self.y + dy / L * BOND }
}

// 元素首字母 → 候选元素（按原子序数从小到大），用于「悬停原子 + 按字母改元素」
// 规则：小写 = 序数小的元素，大写 = 序数大的元素（如 c→C / C→Cl、n→N / N→Na）
export const LETTER_ELEMENTS = {
  h: ['H'], b: ['B', 'Br'], c: ['C', 'Cl'], n: ['N', 'Na'], o: ['O'],
  f: ['F', 'Fe'], p: ['P', 'Pt'], s: ['S', 'Se'], k: ['K'], i: ['I', 'Ir'],
  a: ['Ag', 'Au'], m: ['Mg'], g: ['Ge'], r: ['Ru', 'Rh'], d: ['Dy'],
  e: ['Er'], t: ['Ti'], v: ['V'], w: ['W'], y: ['Y'], z: ['Zn'], u: ['U'],
  l: ['Li'], x: ['Xe']
}

// 按下某个字母键（含大小写）→ 目标元素符号；找不到返回 ''
export function elementForKey(key) {
  if (!key || key.length !== 1 || !/[A-Za-z]/.test(key)) return ''
  const list = LETTER_ELEMENTS[key.toLowerCase()]
  if (!list || !list.length) return ''
  if (list.length === 1) return list[0]
  return key === key.toUpperCase() ? list[1] : list[0]     // 小写=小序数，大写=大序数
}

// 把一组原子缩放进一个方框（供缩略图/预览共用）：返回像素换算与线宽字号
export function fitToBox(atoms, width, height, padding = 6) {
  const xs = atoms.map(a => a.x)
  const ys = atoms.map(a => a.y)
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const spanX = Math.max(maxX - minX, 0.5), spanY = Math.max(maxY - minY, 0.5)
  const scale = Math.max(4, Math.min((width - padding) / spanX, (height - padding) / spanY))
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2
  return {
    scale,
    toPx: (a) => ({ X: (a.x - cx) * scale + width / 2, Y: -(a.y - cy) * scale + height / 2 }),
    fontSize: Math.max(7, Math.min(20, scale * 1.4 * 0.42)),
    bondGap: Math.max(1.2, Math.min(5, scale * 1.4 * 0.11))
  }
}

// 缩略图 SVG（环模板等片段）：同一套渲染函数，避免另写一套画法
export function thumbnailSvg(atoms, bonds, size = 26, padding = 3) {
  if (!atoms || !atoms.length) return ''
  const fit = fitToBox(atoms, size, size, padding)
  return moleculeSvg(atoms, bonds, {
    width: size, height: size, toPx: fit.toPx,
    fontSize: fit.fontSize, bondGap: fit.bondGap,
    showExplicitCH: false, showIndices: false, background: 'none'
  })
}

// 一个分子（原子/键 + 像素换算函数）→ SVG 字符串（预览/导出/缩略图共用同一套画法）
export function moleculeSvg(atoms, bonds, { width, height, toPx, fontSize, bondGap, showExplicitCH, showIndices, background = '#ffffff', dark = false }) {
  const stroke = bondColorFor(dark)
  const parts = [`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    background === 'none' ? '' : `<rect x="0" y="0" width="${width}" height="${height}" fill="${background}"/>`].filter(Boolean)
  for (const b of bonds) {
    const A = atoms.find(a => a.index === b.a)
    const B = atoms.find(a => a.index === b.b)
    if (!A || !B) continue
    const pa = toPx(A), pb = toPx(B)
    const gapA = atomText(A, { showExplicitCH, dark }).label ? fontSize * 0.62 + 2 : 0
    const gapB = atomText(B, { showExplicitCH, dark }).label ? fontSize * 0.62 + 2 : 0
    for (const s of bondSegments(b, pa, pb, { gapA, gapB, bondGap })) {
      parts.push(`<line x1="${s.x1.toFixed(1)}" y1="${s.y1.toFixed(1)}" x2="${s.x2.toFixed(1)}" y2="${s.y2.toFixed(1)}" stroke="${stroke}" stroke-width="2" stroke-linecap="round"/>`)
    }
  }
  for (const a of atoms) {
    const t = atomText(a, { showExplicitCH, dark })
    const p = toPx(a)
    if (t.label) {
      const sub = t.sub ? `<tspan font-size="${(fontSize * 0.68).toFixed(1)}" dy="2.5">${t.sub}</tspan>` : ''
      const chg = t.charge ? `<tspan font-size="${(fontSize * 0.68).toFixed(1)}" dy="-2.5">${t.charge}</tspan>` : ''
      parts.push(`<text x="${p.X.toFixed(1)}" y="${p.Y.toFixed(1)}" text-anchor="middle" dominant-baseline="central"` +
        ` font-family="Arial, Helvetica, sans-serif" font-size="${fontSize.toFixed(1)}" font-weight="500" fill="${t.color}">${t.label}${sub}${chg}</text>`)
    }
    if (showIndices) {
      parts.push(`<text x="${(p.X + 8).toFixed(1)}" y="${(p.Y - 8).toFixed(1)}" font-family="Arial, sans-serif"` +
        ` font-size="${Math.max(9, fontSize * 0.55).toFixed(1)}" fill="#9aa3ad">${a.index}</text>`)
    }
  }
  parts.push('</svg>')
  return parts.join('\n')
}
