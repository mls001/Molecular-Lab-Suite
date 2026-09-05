import json
import os
import sys


def load_config():
    # 1. 优先从环境变量获取项目根目录（由 Electron 主进程设置）
    project_root = os.environ.get('MLS_PROJECT_ROOT')

    if project_root:
        config_path = os.path.join(project_root, 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                print(f'✅ 从环境变量加载配置: {config_path}')
                return json.load(f)

    # 2. 开发环境：从 backend 目录向上查找
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(backend_dir, '..', 'config.json'),  # 项目根目录
        os.path.join(os.getcwd(), 'config.json'),  # 当前工作目录
    ]

    for config_path in possible_paths:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                print(f'✅ 加载配置文件: {config_path}')
                return json.load(f)

    # 3. 如果都找不到，使用默认配置
    print('⚠️ 未找到 config.json，使用默认配置')
    return {"backend": {"host": "127.0.0.1", "port": 8002}, "frontend": {"port": 1145}}


CONFIG = load_config()