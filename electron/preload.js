// 渲染进程 → 主进程 IPC 桥。
// 注意：本文件运行在沙箱化 preload 中，只能 require('electron')，
// 不能 require crypto / electron-store 等模块（它们已全部迁移到主进程 electron/main.js）。
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // ===== 文件/目录操作 =====
  selectDirectory: (options = {}) => ipcRenderer.invoke('select-directory', options),
  selectFile: (options = {}) => ipcRenderer.invoke('select-file', options),

  // ===== 后端地址 =====
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  getBackendWsUrl: () => ipcRenderer.invoke('get-backend-ws-url'),
  getDefaultPaths: () => ipcRenderer.invoke('get-default-paths'),

  // ===== IPC 通信（带白名单） =====
  send: (channel, data) => {
    const allowedChannels = ['terminal-input', 'window-control', 'app-command'];
    if (allowedChannels.includes(channel)) {
      ipcRenderer.send(channel, data);
    } else {
      console.warn(`[preload] 不允许的频道: ${channel}`);
    }
  },
  receive: (channel, func) => {
    const allowedChannels = ['terminal-output', 'window-state', 'backend-status'];
    if (allowedChannels.includes(channel)) {
      ipcRenderer.on(channel, (event, ...args) => func(...args));
    } else {
      console.warn(`[preload] 不允许的频道: ${channel}`);
    }
  },
  removeListener: (channel, func) => {
    ipcRenderer.removeListener(channel, func);
  },

  // ===== 偏好存储（实际读写发生在主进程，密码自动 AES 加密落盘） =====
  storeGet: (key) => ipcRenderer.invoke('store-get', key),
  storeSet: (key, value) => ipcRenderer.invoke('store-set', key, value),
  storeDelete: (key) => ipcRenderer.invoke('store-delete', key),

  // ===== 系统密钥链（keytar，主进程处理） =====
  keytar: {
    setPassword: (password) => ipcRenderer.invoke('keytar-set-password', password),
    getPassword: () => ipcRenderer.invoke('keytar-get-password'),
    deletePassword: () => ipcRenderer.invoke('keytar-delete-password')
  },

  // ===== 应用控制 =====
  quit: () => ipcRenderer.send('app-command', { command: 'quit' }),
  minimize: () => ipcRenderer.send('app-command', { command: 'minimize' }),
  maximize: () => ipcRenderer.send('app-command', { command: 'maximize' }),
  unmaximize: () => ipcRenderer.send('app-command', { command: 'unmaximize' }),
  close: () => ipcRenderer.send('app-command', { command: 'close' }),

  // ===== 系统信息 =====
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  getPlatform: () => process.platform
});
