import { defineStore } from 'pinia'

// 分子在页面之间传递用（分子结构页 → 输入文件生成页）
export const useMoleculeStore = defineStore('molecule', {
  state: () => ({
    molblock: '',
    name: '',
    atoms: [],
    charge: 0,
    mult: 1,
    source: ''
  }),
  actions: {
    put(payload) {
      this.molblock = payload.molblock || ''
      this.name = payload.name || ''
      this.atoms = payload.atoms || []
      this.charge = payload.charge || 0
      this.mult = payload.mult || 1
      this.source = payload.source || ''
    },
    clear() {
      this.molblock = ''
      this.name = ''
      this.atoms = []
      this.source = ''
    }
  }
})
