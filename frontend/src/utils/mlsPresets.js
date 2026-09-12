// 计算资源预设（内存 / 核数）：生成输入、修改GJF、提取扫描 三页共用，避免各写一份。
export const RESOURCE_PRESETS = {
  'hachimi单并行': { nproc: '10', mem: '40GB' },
  'hachimi四并行': { nproc: '4', mem: '10GB' },
  'Tomori八队列': { nproc: '12', mem: '12GB' },
  'students/zstoffice': { nproc: '8', mem: '20GB' },
  'zst106': { nproc: '24', mem: '180GB' }
}

export const DEFAULT_RESOURCE_PRESET = 'students/zstoffice'

// 预设名 → { mem, nproc }（ORCA 额外给出 %maxcore：单核内存 MB）
export function resourceOf(name) {
  const p = RESOURCE_PRESETS[name] || RESOURCE_PRESETS[DEFAULT_RESOURCE_PRESET]
  const memGB = Math.max(1, parseInt(String(p.mem).replace(/[^0-9]/g, ''), 10) || 1)
  const nproc = Math.max(1, parseInt(p.nproc, 10) || 1)
  return { mem: p.mem, nproc: String(p.nproc), maxcore: Math.round(memGB * 1024 / nproc) }
}

export const RESOURCE_PRESET_NAMES = Object.keys(RESOURCE_PRESETS)
