<template>
  <div ref="viewerContainer" style="width:100%;height:100%;min-height:400px;"></div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import $3Dmol from '3dmol'

export default {
  name: 'Mol3DViewer',
  props: {
    coords: {
      type: Array,
      default: () => []
    },
    atoms: {
      type: Array,
      default: () => []
    },
    bonds: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const viewerContainer = ref(null)
    let viewer = null

    const initViewer = () => {
      if (!viewerContainer.value) return
      viewer = $3Dmol.createViewer(viewerContainer.value, {
        backgroundColor: 'white',
        width: '100%',
        height: '100%'
      })
      viewer.setStyle({}, { stick: { radius: 0.15 } })
      viewer.zoomTo()
      viewer.render()
    }

    const updateStructure = () => {
      if (!viewer) return
      if (props.coords && props.coords.length > 0) {
        // 构建 XYZ 格式字符串
        let xyz = ''
        if (props.atoms && props.atoms.length === props.coords.length) {
          for (let i = 0; i < props.atoms.length; i++) {
            const pos = props.coords[i]
            xyz += `${props.atoms[i].symbol} ${pos[0]} ${pos[1]} ${pos[2]}\n`
          }
        } else {
          // 如果没提供原子信息，就用 C 替代显示骨架
          for (let i = 0; i < props.coords.length; i++) {
            const pos = props.coords[i]
            xyz += `C ${pos[0]} ${pos[1]} ${pos[2]}\n`
          }
        }
        // 清空并加载新模型
        viewer.removeAllModels()
        const model = viewer.addModel()
        model.addModel(xyz, 'xyz')
        model.setStyle({}, { stick: { radius: 0.15 }, sphere: { radius: 0.3 } })
        viewer.zoomTo()
        viewer.render()
      }
    }

    onMounted(() => {
      initViewer()
    })

    watch(() => props.coords, () => {
      updateStructure()
    }, { deep: true })

    onBeforeUnmount(() => {
      if (viewer) {
        viewer.removeAllModels()
        viewer = null
      }
    })

    return { viewerContainer }
  }
}
</script>