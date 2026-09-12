// 激发态分析结果的「成对摆放」规则（NTO / 空穴-电子），抽出来便于单测
// NTO：占据 NTO 在左、对应的空 NTO 在右；空穴-电子：Hole 在左、Electron 在右

/** 单重态标 S，三重态（或 mult=3）标 T */
export function spinLabel(o) {
  const s = (o && o.spin) || ''
  if (s === 'T' || s === 'S') return s
  return o && o.mult === 3 ? 'T' : 'S'
}

/**
 * S1 / T2 这样的独立标号：S 与 T 各自从 1 数
 * （ORCA 的 SOC 输出里两者都用 1、2、3… 编号，直接显示会出现两个 S1/T1 之外的混淆）
 */
export function stateLabel(o, states = []) {
  const key = o && (o.order != null ? o.order : o.state)
  const s = (states || []).find((x) => (x.order != null ? x.order : x.state) === key)
  const spin = (s && s.spin) || (o && o.spin) || 'S'
  const idx = s && s.spin_index != null ? s.spin_index : (o && o.state != null ? o.state : '')
  return `${spin === 'T' ? 'T' : 'S'}${idx}`
}

/** 图片右下角标注：Hole/Electron + NTO 对序号 + 贡献值 + 该激发态振子强度 */
export function ntoNote(item, cube, states = []) {
  const key = item && (item.order != null ? item.order : item.state)
  const s = (states || []).find((x) => (x.order != null ? x.order : x.state) === key)
  const f = s && s.f != null ? Number(s.f) : null
  const side = cube && cube.side === 'vir' ? 'Electron' : 'Hole'
  const parts = [stateLabel(item, states)]
  if (cube && cube.index != null) parts.push(`NTO${cube.index} (${side})`)
  if (cube && cube.pair) parts.push(`pair NTO${cube.pair}`)
  if (cube && cube.contrib != null) parts.push(`${cube.contrib.toFixed(1)}%`)
  if (f != null) parts.push(`f=${f.toFixed(4)}`)
  return parts.join('  ')
}

/** 图片右下角标注：该态的自旋标号 + Sr / D 指数（sobereva.com/434 的图也是这么标的） */
export function heNote(item, states = []) {
  const m = {}
  ;((item && item.metrics) || []).forEach((r) => { m[r.key] = r })
  const parts = [stateLabel(item, states)]
  if (m.Sr) parts.push(`Sr=${m.Sr.value.toFixed(3)}`)
  if (m.D) parts.push(`D=${m.D.value.toFixed(2)} A`)
  return parts.join('  ')
}

/** 本征值 → 百分比文字（没有就不显示） */
function eigenText(c) {
  return c && c.eigen != null ? ` · ${(c.eigen * 100).toFixed(1)}%` : ''
}

/**
 * 把一个激发态结果的 cube 列表变成一行行「左/右」图
 * @param {string} mode 'nto' | 'he'
 * @param {object} item { cubes: [{kind, side, index, eigen, cub}] }
 * @param {function} t i18n 函数（$t）
 * @returns {Array<{key,left,right,leftLabel,rightLabel}>}
 */
export function pairRows(mode, item, t = (s) => s) {
  const by = {}
  ;((item && item.cubes) || []).forEach((c) => { by[c.kind] = c })
  const rows = []
  if (mode === 'nto') {
    // 占据侧按 NTO 序号从大到小（本征值最大的一对排最前），空侧从小到大
    const occ = ((item && item.cubes) || []).filter((c) => c.side === 'occ').sort((a, b) => b.index - a.index)
    const vir = ((item && item.cubes) || []).filter((c) => c.side === 'vir').sort((a, b) => a.index - b.index)
    occ.forEach((c, i) => {
      const v = vir[i]
      // NTO 对按物理含义叫 Hole（占据、电子离开处）与 Electron（空、电子去处）
      rows.push({
        key: `nto${i}`,
        left: c,
        right: v || null,
        leftLabel: `NTO${c.index} Hole${eigenText(c)}`,
        rightLabel: v ? `NTO${v.index} Electron${eigenText(v)}` : ''
      })
    })
    // 只有空轨道没有占据（异常情况）也要显示出来
    if (!occ.length && vir.length) {
      vir.forEach((v, i) => rows.push({
        key: `ntov${i}`, left: null, right: v, leftLabel: '',
        rightLabel: `NTO${v.index} Electron${eigenText(v)}`
      }))
    }
    return rows
  }
  if (by.hole || by.electron) {
    rows.push({ key: 'he', left: by.hole, right: by.electron, leftLabel: 'Hole', rightLabel: 'Electron' })
  }
  if (by.Chole || by.Cele) {
    rows.push({ key: 'cc', left: by.Chole, right: by.Cele, leftLabel: 'Chole', rightLabel: 'Cele' })
  }
  if (by.Sr || by.CDD) {
    rows.push({ key: 'sr', left: by.Sr, right: by.CDD, leftLabel: 'Sr', rightLabel: 'CDD' })
  }
  if (by.transition) {
    rows.push({ key: 'td', left: by.transition, right: null, leftLabel: 'Transition density', rightLabel: '' })
  }
  return rows.filter((r) => r.left || r.right)
}
