// Nature 子刊风格绘图基元：低饱和配色、发丝线、克制的刻度与标签。
// 供 SOC / TD 能级图共用，保证两张图视觉语言一致。
export const PALETTE = {
  singlet: '#B0413E',     // 单线态（低饱和砖红）
  triplet: '#2E5E8E',     // 三线态（低饱和钢蓝）
  other: '#55575A',
  axis: '#1A1A1A',
  grid: '#E6E6E6',
  text: '#1A1A1A',
  textMuted: '#5F6368',
  connector: '#9AA0A6',
  guide: '#C9CDD2'
}

export const FONT_STACK = "'Helvetica Neue', Helvetica, Arial, 'Microsoft YaHei', sans-serif"

export function font(size, weight = '400') {
  return `${weight} ${Math.max(6, Math.round(size))}px ${FONT_STACK}`
}

/** 1px 发丝线对齐（避免模糊的 2px 灰线） */
export function crisp(v) {
  return Math.round(v) + 0.5
}

/** 1/2/5 取整刻度步长 */
export function niceStep(range, target = 6) {
  const raw = range / Math.max(1, target)
  const mag = Math.pow(10, Math.floor(Math.log10(raw || 1)))
  const norm = raw / mag
  const step = norm >= 5 ? 5 : norm >= 2 ? 2 : 1
  return step * mag
}

export function tickValues(min, max, target = 6) {
  const step = niceStep(max - min, target)
  const out = []
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(Number(v.toFixed(10)))
  return out
}

/**
 * 画能量坐标轴：论文级极简 —— 只保留左轴细线 + 朝外刻度 + 左上角横向单位标注。
 * 能级图不需要横轴，也不画网格与图例（标签自身已用颜色区分 S / T）。
 */
export function drawAxes(ctx, { L, T, R, B, min, max, sf = 1, unit = 'Energy (eV)', title = null, target = 5 }) {
  const yOf = (v) => B - ((v - min) / (max - min || 1)) * (B - T)
  const values = tickValues(min, max, target)
  ctx.save()
  ctx.lineWidth = 1
  ctx.strokeStyle = PALETTE.axis
  ctx.fillStyle = PALETTE.text

  // 左轴
  ctx.beginPath()
  ctx.moveTo(crisp(L), crisp(T))
  ctx.lineTo(crisp(L), crisp(B))
  ctx.stroke()

  // 刻度（朝外）+ 数值
  ctx.font = font(10 * sf)
  ctx.fillStyle = PALETTE.textMuted
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  values.forEach(v => {
    const y = crisp(yOf(v))
    if (y < T - 1 || y > B + 1) return
    ctx.beginPath()
    ctx.strokeStyle = PALETTE.axis
    ctx.moveTo(L - 3.5 * sf, y)
    ctx.lineTo(L, y)
    ctx.stroke()
    ctx.fillText(v.toFixed(2), L - 5.5 * sf, y)
  })

  // 单位：横向放在轴上端左侧（比竖排轴标题更克制）
  ctx.textAlign = 'right'
  ctx.textBaseline = 'bottom'
  ctx.fillStyle = PALETTE.text
  ctx.font = font(10 * sf, '500')
  ctx.fillText(title || unit, L - 5.5 * sf, T - 5 * sf)
  ctx.restore()
  return yOf
}

/** 能级横线（圆头 + 轻微外发光留白，看起来更"论文"） */
export function drawLevel(ctx, { cx, y, half, color, sf = 1, width = 2 }) {
  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = Math.max(1.6, width * sf)
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(cx - half, crisp(y))
  ctx.lineTo(cx + half, crisp(y))
  ctx.stroke()
  ctx.restore()
}

/** 能量标签：在线段一侧，带小引线点 */
export function drawEnergyLabel(ctx, { x, y, text, color, align = 'left', sf = 1 }) {
  ctx.save()
  ctx.font = font(11 * sf, '500')
  ctx.fillStyle = color
  ctx.textAlign = align
  ctx.textBaseline = 'middle'
  ctx.fillText(text, x, y)
  ctx.restore()
}
