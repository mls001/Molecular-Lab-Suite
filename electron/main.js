const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');

let mainWindow;
let backendProcess = null;
let isQuitting = false;

// ===== 读取配置文件 =====
function loadConfig() {
  const isDev = process.env.NODE_ENV === 'development';
  let configPath;
  if (isDev) {
    configPath = path.join(__dirname, '..', 'config.json');
  } else {
    // 打包后从 resources 目录读取
    configPath = path.join(process.resourcesPath, 'config.json');
  }
  if (fs.existsSync(configPath)) {
    try {
      const content = fs.readFileSync(configPath, 'utf-8');
      return JSON.parse(content);
    } catch (e) {
      console.warn('读取 config.json 失败，使用默认配置', e);
    }
  }
  // 默认端口改为 8002（与 fallback 一致）
  return { backend: { host: '127.0.0.1', port: 8002 }, frontend: { port: 1145 } };
}

const CONFIG = loadConfig();
const BACKEND_HOST = CONFIG.backend?.host ?? '127.0.0.1';
const BACKEND_PORT = CONFIG.backend?.port ?? 8002;   // 直接使用 CONFIG 中的值，若为 undefined 则用 8002
const FRONTEND_PORT = CONFIG.frontend?.port ?? 1145;

// ===== 缓存目录（应用根目录下的 cache 文件夹） =====
function getCacheDir() {
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    // 开发环境：项目根目录下的 cache
    return path.join(__dirname, '..', 'cache');
  } else {
    // 生产环境：应用安装根目录（.exe 所在目录）下的 cache
    const appRoot = path.dirname(process.resourcesPath);
    return path.join(appRoot, 'cache');
  }
}
const cacheDir = getCacheDir();

// ===== 获取后端可执行文件路径 =====
function getBackendPath() {
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    const exePath = path.join(__dirname, '..', 'backend', 'dist', 'mls-backend.exe');
    if (fs.existsSync(exePath)) {
      return { exe: exePath, args: [] };
    } else {
      const venvPython = path.join(__dirname, '..', 'mlslib', 'Scripts', 'python.exe');
      const pythonExe = fs.existsSync(venvPython) ? venvPython : 'python';
      const startScript = path.join(__dirname, '..', 'backend', 'start.py');
      return { exe: pythonExe, args: [startScript] };
    }
  } else {
    const resourcesPath = process.resourcesPath;
    let exePath = path.join(resourcesPath, 'mls-backend.exe');
    if (!fs.existsSync(exePath)) {
      exePath = path.join(resourcesPath, 'backend', 'mls-backend.exe');
    }
    if (!fs.existsSync(exePath)) {
      console.error('未找到 mls-backend.exe，请检查打包配置');
      return { exe: 'python', args: [] };
    }
    return { exe: exePath, args: [] };
  }
}

// ===== 强制杀死所有 mls-backend.exe 进程（含子进程） =====
function killAllBackendProcesses() {
  return new Promise((resolve) => {
    exec('taskkill /f /t /im mls-backend.exe', (error, stdout, stderr) => {
      if (error) {
        console.log('没有残留的 mls-backend.exe 进程或已清除');
      } else {
        console.log('已强制终止所有 mls-backend.exe 进程（含子进程）');
        console.log(stdout);
      }
      resolve();
    });
  });
}

// ===== 清除缓存目录（同步删除，确保退出前完成） =====
function clearCache() {
  try {
    if (fs.existsSync(cacheDir)) {
      fs.rmSync(cacheDir, { recursive: true, force: true });
      console.log('✅ 缓存目录已清除:', cacheDir);
    }
  } catch (err) {
    // 不检查权限，仅打印警告，忽略错误
    console.warn('清除缓存失败:', err.message);
  }
}

// ===== 启动后端进程 =====
function startBackend() {
  const { exe, args } = getBackendPath();
  if (!fs.existsSync(exe)) {
    console.error(`后端可执行文件不存在: ${exe}`);
    return;
  }
  console.log(`启动后端: ${exe} ${args.join(' ')}`);

  const env = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    MLS_PRODUCTION: 'true'
  };

  backendProcess = spawn(exe, args, {
    env: env,
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
  });
}

// ===== 创建窗口 =====
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    },
    icon: path.join(__dirname, '..', 'build', 'icon.ico')
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

// ===== IPC：选择目录 =====
ipcMain.handle('select-directory', async (event, options = {}) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
    title: options.title || '选择文件夹',
    defaultPath: options.defaultPath || app.getPath('documents')
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('get-backend-url', () => {
  return `http://${BACKEND_HOST}:${BACKEND_PORT}`;
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
  await killAllBackendProcesses();
  // 清除缓存
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

// 如果主进程崩溃，尝试清理
process.on('exit', () => {
  if (backendProcess) {
    backendProcess.kill('SIGKILL');
  }
  try {
    require('child_process').execSync('taskkill /f /t /im mls-backend.exe', { stdio: 'ignore' });
  } catch (e) { /* ignore */ }
  // 尝试清除缓存（同步）
  try {
    if (fs.existsSync(cacheDir)) {
      fs.rmSync(cacheDir, { recursive: true, force: true });
    }
  } catch (e) { /* ignore */ }
});