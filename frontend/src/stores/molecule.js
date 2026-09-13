import { defineStore } from 'pinia'

// 分子在页面之间传递用（分子结构页 → 输入文件生成页）
// rev：每放进一个新的分子就 +1，接收页据此判断"要不要重新载入"（页面被 keep-alive 缓存时也能收到）
export const useMoleculeStore = defineStore('molecule', {
  state: () => ({
    molblock: '',
    name: '',
    atoms: [],
    charge: 0,
    mult: 1,
    source: '',
    rev: 0
  }),
  actions: {
    put(payload) {
      this.molblock = payload.molblock || ''
      this.name = payload.name || ''
      this.atoms = payload.atoms || []
      this.charge = payload.charge || 0
      this.mult = payload.mult || 1
      this.source = payload.source || ''
      this.rev += 1
    },
    clear() {
      this.molblock = ''
      this.name = ''
      this.atoms = []
      this.source = ''
      this.rev += 1
    }
  }
})
