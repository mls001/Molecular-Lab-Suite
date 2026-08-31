import json
import os
import sys


def load_config():
    # 尝试从多个可能的位置查找 config.json
    possible_paths = []

    # 1. 如果是 PyInstaller 打包，使用 sys._MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        possible_paths.append(os.path.join(sys._MEIPASS, 'config.json'))

    # 2. 从当前文件所在目录向上查找项目根目录
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    possible_paths.append(os.path.join(project_root, 'config.json'))

    # 3. 当前工作目录
    possible_paths.append(os.path.join(os.getcwd(), 'config.json'))

    for config_path in possible_paths:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

    # 默认配置
    return {"backend": {"host": "127.0.0.1", "port": 8002}, "frontend": {"port": 1145}}


CONFIG = load_config()
