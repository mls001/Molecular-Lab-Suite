const { app, BrowserWindow, ipcMain, dialog, Menu } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const keytar = require('keytar');  // 新增
const { createCipheriv, createDecipheriv, randomBytes, scryptSync } = require('crypto');
const Store = require('electron-store');

// ===== 本地偏好存储（仅主进程可用；electron-store v8+ 不支持渲染进程） =====
// 密码字段在落盘前用 AES-256-CBC 加密（密钥由主密码经 scrypt 派生）。
const STORE_MASTER_KEY = process.env.MLS_MASTER_PASSWORD || 'mls-default-master-key-2024';

function encryptText(text) {
  if (!text) return '';
  const salt = randomBytes(16);
  const iv = randomBytes(16);
  const key = scryptSync(STORE_MASTER_KEY, salt, 32);
  const cipher = createCipheriv('aes-256-cbc', key, iv);
  let encrypted = cipher.update(text, 'utf-8', 'hex');
  encrypted += cipher.final('hex');
  return `${salt.toString('hex')}:${iv.toString('hex')}:${encrypted}`;
}

function decryptText(encryptedText) {
  if (!encryptedText) return '';
  try {
    const parts = encryptedText.split(':');
    if (parts.length !== 3) {
      // 兼容旧的纯 Base64 格式
      try { return Buffer.from(encryptedText, 'base64').toString('utf-8'); } catch (e) { return ''; }
    }
    const salt = Buffer.from(parts[0], 'hex');
    const iv = Buffer.from(parts[1], 'hex');
    const key = scryptSync(STORE_MASTER_KEY, salt, 32);
    const decipher = createDecipheriv('aes-256-cbc', key, iv);
    let decrypted = decipher.update(parts[2], 'hex', 'utf-8');
    decrypted += decipher.final('utf-8');
    return decrypted;
  } catch (error) {
    console.error('[Store] 解密失败:', error.message);
    return '';
  }
}

const store = new Store({
  name: 'mls-preferences',
  defaults: {
    remote: { host: '', port: 22, username: '', password: '' },
    window: { width: 1400, height: 900, maximized: false }
  }
});

// 读取：remote 键返回时自动解密 password
function storeGetValue(key) {
  const value = store.get(key);
  if (key === 'remote' && value && value.password) {
    return { ...value, password: decryptText(value.password) };
  }
  return value;
}

// 写入：remote 键在落盘前自动加密 password
function storeSetValue(key, value) {
  if (key === 'remote' && value && value.password) {
    store.set(key, { ...value, password: encryptText(value.password) });
  } else {
    store.set(key, value);
  }
}

ipcMain.handle('store-get', (event, key) => storeGetValue(key));
ipcMain.handle('store-set', (event, key, value) => {
  storeSetValue(key, value);
  return true;
});
ipcMain.handle('store-delete', (event, key) => {
  store.delete(key);
  return true;
});

// ===== keytar 常量 =====
const KEYTAR_SERVICE = 'MolecularLabSuite';
const KEYTAR_ACCOUNT = 'server_password';

// ===== keytar IPC 处理器 =====
// 保存密码到系统密钥链
ipcMain.handle('keytar-set-password', async (event, password) => {
  try {
    if (password) {
      await keytar.setPassword(KEYTAR_SERVICE, KEYTAR_ACCOUNT, password);
      console.log('[Keytar] 密码已保存到系统密钥链');
      return { success: true };
    } else {
      // 如果密码为空，删除存储的密码
      await keytar.deletePassword(KEYTAR_SERVICE, KEYTAR_ACCOUNT);
      console.log('[Keytar] 密码已从系统密钥链删除');
      return { success: true };
    }
  } catch (error) {
    console.error('[Keytar] 保存密码失败:', error);
    return { success: false, error: error.message };
  }
});

// 从系统密钥链读取密码
ipcMain.handle('keytar-get-password', async () => {
  try {
    const password = await keytar.getPassword(KEYTAR_SERVICE, KEYTAR_ACCOUNT);
    console.log('[Keytar] 从系统密钥链读取密码:', password ? '已找到' : '未找到');
    return { success: true, password: password || '' };
  } catch (error) {
    console.error('[Keytar] 读取密码失败:', error);
    return { success: false, error: error.message, password: '' };
  }
});

// 从系统密钥链删除密码
ipcMain.handle('keytar-delete-password', async () => {
  try {
    await keytar.deletePassword(KEYTAR_SERVICE, KEYTAR_ACCOUNT);
    console.log('[Keytar] 密码已从系统密钥链删除');
    return { success: true };
  } catch (error) {
    console.error('[Keytar] 删除密码失败:', error);
    return { success: false, error: error.message };
  }
});

let mainWindow;
let backendProcess = null;
let isQuitting = false;

// ===== 读取配置文件 =====
function loadConfig() {
  const isDev = process.env.NODE_ENV === 'development';
  let configPath;

  if (isDev) {
    // 开发环境：项目根目录
    configPath = path.join(__dirname, '..', 'config.json');
  } else {
    // 生产环境（打包后）：
    // 1. 优先读取 .exe 同级目录（用户方便修改）
    const exeDir = path.dirname(app.getPath('exe'));
    const exeConfigPath = path.join(exeDir, 'config.json');

    if (fs.existsSync(exeConfigPath)) {
      configPath = exeConfigPath;
      console.log('📁 使用 .exe 同级目录的 config.json');
    } else {
      // 2. 回退到 resources 目录（打包时内置的默认配置）
      configPath = path.join(process.resourcesPath, 'config.json');
      console.log('📁 使用 resources 目录的 config.json');
    }
  }

  if (fs.existsSync(configPath)) {
    try {
      const content = fs.readFileSync(configPath, 'utf-8');
      const config = JSON.parse(content);
      console.log(`✅ 已加载配置文件: ${configPath}`);
      console.log(`   Backend: ${config.backend?.host}:${config.backend?.port}`);
      return config;
    } catch (e) {
      console.warn('读取 config.json 失败，使用默认配置', e);
    }
  } else {
    console.warn(`⚠️ 配置文件不存在: ${configPath}，使用默认配置`);
  }

  // 默认配置
  return { backend: { host: '127.0.0.1', port: 8002 }, frontend: { port: 1145 } };
}

const CONFIG = loadConfig();
const BACKEND_HOST = CONFIG.backend?.host ?? '127.0.0.1';
const BACKEND_PORT = CONFIG.backend?.port ?? 8002;
const FRONTEND_PORT = CONFIG.frontend?.port ?? 1145;

console.log(`🚀 后端服务地址: http://${BACKEND_HOST}:${BACKEND_PORT}`);

// ===== 缓存目录 =====
function getCacheDir() {
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    return path.join(__dirname, '..', 'cache');
  } else {
    const appRoot = path.dirname(process.resourcesPath);
    return path.join(appRoot, 'cache');
  }
}
const cacheDir = getCacheDir();

// ===== 后端启动路径解析 =====
// 设计：本应用以打包版（electron-builder + PyInstaller 后端 exe）为唯一分发形态。
//   生产环境：仅使用 PyInstaller 打包的自包含后端 mls-backend.exe（找不到则明确报错）
//   开发环境：venv (mlslib) python + backend/start.py，找不到时回退系统 python
function fileExists(p) {
  try { return fs.existsSync(p); } catch (e) { return false; }
}

function findOnPath(cmd) {
  try {
    const out = execSync(`where ${cmd}`).toString();
    const first = out.split(/\r?\n/).map(s => s.trim()).find(Boolean);
    return first || null;
  } catch (e) {
    return null;
  }
}

function getBackendPath() {
  const isDev = process.env.NODE_ENV === 'development';

  // ===== 开发环境：Python 源码方式（venv） =====
  if (isDev) {
    const venvPython = path.join(__dirname, '..', 'mlslib', 'Scripts', 'python.exe');
    const pythonExe = fileExists(venvPython) ? venvPython : findOnPath('python');
    const startScript = path.join(__dirname, '..', 'backend', 'start.py');
    if (!pythonExe || !fileExists(startScript)) {
      console.error(`❌ 开发后端启动环境不完整: python=${pythonExe}, script=${startScript}`);
      return null;
    }
    console.log(`🐍 Python: ${pythonExe}`);
    console.log(`📄 启动脚本: ${startScript}`);
    // 工作目录必须是 backend 目录（start.py 依赖其中的 config.py / app 包）
    return { exe: pythonExe, args: [startScript], kind: 'python', cwd: path.dirname(startScript) };
  }

  // ===== 生产环境（仅打包运行）：只认 PyInstaller 后端 exe =====
  const resourcesPath = process.resourcesPath;
  const exeDir = path.dirname(app.getPath('exe'));
  const exeCandidates = [
    path.join(resourcesPath, 'backend', 'dist', 'mls-backend.exe'),
    path.join(resourcesPath, 'backend', 'mls-backend.exe'),
    path.join(resourcesPath, 'mls-backend.exe'),
    path.join(exeDir, 'backend', 'dist', 'mls-backend.exe'),
    path.join(exeDir, 'mls-backend.exe'),
  ];
  for (const exePath of exeCandidates) {
    if (fileExists(exePath)) {
      console.log(`✅ 使用打包后端可执行文件: ${exePath}`);
      return { exe: exePath, args: [], kind: 'exe', cwd: exeDir };
    }
  }

  console.error('❌ 生产环境未找到打包的后端可执行文件 mls-backend.exe');
  return null;
}

// ===== 强制杀死所有 Python 后端进程 =====
function killBackendProcesses() {
  return new Promise((resolve) => {
    // 通过端口查找并杀死进程（Windows）
    exec(`for /f "tokens=5" %a in ('netstat -aon ^| find ":${BACKEND_PORT}" ^| find "LISTENING"') do taskkill /f /pid %a`,
      (error, stdout, stderr) => {
        if (error) {
          console.log('没有找到占用端口的进程');
        } else {
          console.log(`已清理占用端口 ${BACKEND_PORT} 的进程`);
        }
        resolve();
      }
    );
  });
}

// ===== 清除缓存 =====
function clearCache() {
  try {
    if (fs.existsSync(cacheDir)) {
      fs.rmSync(cacheDir, { recursive: true, force: true });
      console.log('✅ 缓存目录已清除:', cacheDir);
    }
  } catch (err) {
    console.warn('清除缓存失败:', err.message);
  }
}

// ===== 启动后端进程 =====
function startBackend() {
  const backendInfo = getBackendPath();
  if (!backendInfo) {
    console.error('无法找到后端启动文件，请检查配置');
    showBackendFatal(
      '无法启动后端服务',
      '未找到可用的后端运行环境。\n\n请重新安装本应用，或确认安装目录下存在 mls-backend.exe / backend 目录。'
    );
    return null;
  }

  const { exe, args, cwd } = backendInfo;

  // 获取项目根目录（用于后端查找 config.json）
  let projectRoot;
  if (process.env.NODE_ENV === 'development') {
    projectRoot = path.join(__dirname, '..');
  } else {
    const exeDir = path.dirname(app.getPath('exe'));
    // 与 loadConfig 的读取顺序保持一致：.exe 同级 config.json 优先，其次 resources/config.json
    projectRoot = exeDir;
    if (!fileExists(path.join(exeDir, 'config.json'))) {
      const resConfig = path.join(process.resourcesPath, 'config.json');
      if (fileExists(resConfig)) {
        projectRoot = process.resourcesPath;
      }
    }
  }

  console.log(`🚀 启动后端: ${exe} ${args.join(' ')}`);
  console.log(`📁 项目根目录: ${projectRoot}`);

  const env = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
    MLS_PRODUCTION: process.env.NODE_ENV !== 'development' ? 'true' : 'false',
    MLS_PROJECT_ROOT: projectRoot,
    // 后端持久数据（预设/密钥等）写入用户数据目录，避免 PyInstaller 临时目录被清空导致丢失
    MLS_USER_DATA: app.getPath('userData'),
  };

  backendProcess = spawn(exe, args, {
    env: env,
    cwd: cwd || projectRoot,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    shell: false,
    detached: false
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data}`);
  });
  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data}`);
  });
  backendProcess.on('close', (code) => {
    console.log(`后端进程退出，代码: ${code}`);
    backendProcess = null;
  });
  backendProcess.on('error', (err) => {
    console.error(`启动后端失败: ${err.message}`);
    showBackendFatal(
      '后端启动失败',
      `无法启动后端服务：${err.message}\n\n` +
      '请确认：\n' +
      '1. 应用安装完整（包含后端文件）；\n' +
      '2. 已安装 Python 且可用（未随应用打包时）；\n' +
      '3. 端口 ' + BACKEND_PORT + ' 未被其他程序占用。'
    );
    backendProcess = null;
  });

  return backendProcess;
}

// 后端致命错误提示（窗口就绪后用对话框，否则仅控制台日志）
function showBackendFatal(title, message) {
  console.error(`[Backend] ${title}: ${message}`);
  if (mainWindow && !mainWindow.isDestroyed()) {
    try {
      dialog.showErrorBox(title, message);
    } catch (e) { /* ignore */ }
  }
}

// ===== 创建窗口 =====
function createWindow() {
  // 隐藏默认 File/Edit 菜单（用户要求上方菜单行隐藏）
  Menu.setApplicationMenu(null)
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 900,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // preload.js 仅桥接 IPC（不再 require crypto/electron-store），可安全保持沙箱开启
      sandbox: true
    },
    icon: path.join(__dirname, '..', 'build', 'icon.ico')
  });

  // F12 快捷键：打开/关闭开发者工具（方便排查）
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && input.key === 'F12') {
      event.preventDefault();
      const wc = mainWindow.webContents;
      if (wc.isDevToolsOpened()) wc.closeDevTools();
      else wc.openDevTools({ mode: 'detach' });
    }
  });

  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    mainWindow.loadURL(`http://localhost:${FRONTEND_PORT}`);
    mainWindow.webContents.openDevTools();
  } else {
    const resourcesPath = process.resourcesPath;
    let indexPath = path.join(resourcesPath, 'frontend', 'dist', 'index.html');
    if (!fs.existsSync(indexPath)) {
      indexPath = path.join(__dirname, '..', 'frontend', 'dist', 'index.html');
    }
    mainWindow.loadFile(indexPath);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ===== IPC 处理器 =====
ipcMain.handle('select-directory', async (event, options = {}) => {
  const opts = {
    properties: ['openDirectory', 'createDirectory'],
    title: options.title || '选择文件夹',
    defaultPath: options.defaultPath || app.getPath('documents')
  };
  // 窗口不可用时退化为无父窗口的系统对话框
  const result = mainWindow && !mainWindow.isDestroyed()
    ? await dialog.showOpenDialog(mainWindow, opts)
    : await dialog.showOpenDialog(opts);
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('select-file', async (event, options = {}) => {
  const opts = {
    properties: ['openFile'],
    title: options.title || '选择文件',
    filters: options.filters || [{ name: 'All Files', extensions: ['*'] }],
    defaultPath: options.defaultPath || app.getPath('documents')
  };
  const result = mainWindow && !mainWindow.isDestroyed()
    ? await dialog.showOpenDialog(mainWindow, opts)
    : await dialog.showOpenDialog(opts);
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('get-backend-url', () => {
  const url = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
  console.log(`[IPC] 返回后端地址: ${url}`);
  return url;
});

ipcMain.handle('get-backend-ws-url', () => {
  const url = `ws://${BACKEND_HOST}:${BACKEND_PORT}`;
  return url;
});

// FTP 等使用的默认路径（Windows=桌面，Linux=/home/<用户> 由前端拼用户名）
ipcMain.handle('get-default-paths', () => {
  return {
    platform: process.platform,
    desktop: app.getPath('desktop'),
    home: app.getPath('home')
  };
});

// ===== 优雅退出 =====
async function quitApp() {
  if (isQuitting) return;
  isQuitting = true;
  console.log('正在关闭应用，清理后端进程...');

  if (backendProcess) {
    backendProcess.kill('SIGKILL');
    backendProcess = null;
  }

  await killBackendProcesses();
  clearCache();
  console.log('清理完成，退出应用');
  app.exit(0);
}

// ===== 应用生命周期 =====
app.whenReady().then(() => {
  startBackend();
  setTimeout(createWindow, 2000);
});

app.on('window-all-closed', () => {
  quitApp();
});

app.on('before-quit', (event) => {
  if (!isQuitting) {
    event.preventDefault();
    quitApp();
  }
});

// 进程退出时的清理
process.on('exit', () => {
  if (backendProcess) {
    backendProcess.kill('SIGKILL');
  }
  try {
    exec(`for /f "tokens=5" %a in ('netstat -aon ^| find ":${BACKEND_PORT}" ^| find "LISTENING"') do taskkill /f /pid %a`,
      { stdio: 'ignore' }
    );
  } catch (e) { /* ignore */ }
  try {
    if (fs.existsSync(cacheDir)) {
      fs.rmSync(cacheDir, { recursive: true, force: true });
    }
  } catch (e) { /* ignore */ }
});