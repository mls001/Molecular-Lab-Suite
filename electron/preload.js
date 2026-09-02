const { contextBridge, ipcRenderer } = require('electron');
const Store = require('electron-store');

const store = new Store({
  name: 'mls-preferences',
  defaults: {
    remote: {
      host: '',
      port: 22,
      username: ''
    }
  }
});

contextBridge.exposeInMainWorld('electronAPI', {
  selectDirectory: (options = {}) => ipcRenderer.invoke('select-directory', options),
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  send: (channel, data) => ipcRenderer.send(channel, data),
  receive: (channel, func) => ipcRenderer.on(channel, (event, ...args) => func(...args)),
  // 存储方法
  storeGet: (key) => store.get(key),
  storeSet: (key, value) => store.set(key, value),
  storeDelete: (key) => store.delete(key)
});