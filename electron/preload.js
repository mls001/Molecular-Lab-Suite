const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // 选择文件夹（返回路径）
  selectDirectory: (options = {}) => {
    return ipcRenderer.invoke('select-directory', options);
  },
  // 可以添加其他需要暴露的方法
  send: (channel, data) => ipcRenderer.send(channel, data),
  receive: (channel, func) => ipcRenderer.on(channel, (event, ...args) => func(...args))
});