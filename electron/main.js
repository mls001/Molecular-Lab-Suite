const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');

let mainWindow;
let backendProcess = null;
let isQuitting = false; // 防止重复退出

// ===== 读取配置文件 =====
function loadConfig() {
  const configPath = path.join(__dirname, '..', 'config.json');
  if (fs.existsSync(configPath)) {
    try {
      const content = fs.readFileSync(configPath, 'utf-8');
      return JSON.parse(content);
    } catch (e) {
      console.warn('读取 config.json 失败，使用默认配置', e);
    }
  }
  return { backend: { host: '127.0.0.1', port: 8000 }, frontend: { port: 1145 } };
}

const CONFIG = loadConfig();
const BACKEND_HOST = CONFIG.backend?.host || '127.0.0.1';
const BACKEND_PORT = CONFIG.backend?.port || 8000;
const FRONTEND_PORT = CONFIG.frontend?.port || 1145;

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
    // /f 强制 /t 终止进程树 /im 按映像名称
    exec('taskkill /f /t /im mls-backend.exe', (error, stdout, stderr) => {
      if (error) {
        // 如果没有找到进程，taskkill 会返回错误，但我们忽略
        console.log('没有残留的 mls-backend.exe 进程或已清除');
      } else {
        console.log('已强制终止所有 mls-backend.exe 进程（含子进程）');
        console.log(stdout);
      }
      resolve();
    });
  });
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
});