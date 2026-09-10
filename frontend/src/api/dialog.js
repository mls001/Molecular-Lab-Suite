// 目录/文件选择统一入口。
//
// 现在统一走「应用内路径选择器」（LocalPathPicker）：它会把当前目录下的**全部文件与子目录**
// 都列出来，用户可以通过看到的文件内容确认自己是否选对了文件夹；同时支持直接粘贴路径、
// 常用位置/盘符跳转、按名称过滤。若需要系统的文件夹对话框（例如访问网络位置），
// 选择器内提供「系统对话框…」按钮兜底调用 Electron 原生对话框。
import { usePathPickerStore } from '@/stores/pathPicker'

export async function pickDirectory(title, initialPath = '') {
  const picker = usePathPickerStore()
  return await picker.open({ title, initialPath, mode: 'dir' })
}

// 选择单个文件（如 Gaussian .log）：extensions 仅用于高亮/可选过滤，默认仍显示全部文件
export async function pickFile(title, extensions = ['*'], initialPath = '') {
  const picker = usePathPickerStore()
  return await picker.open({ title, initialPath, mode: 'file', extensions })
}
