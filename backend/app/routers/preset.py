from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os
from typing import List, Optional
from app.utils.crypto_utils import encrypt_password, decrypt_password

router = APIRouter()

# 预设存储文件。
# 打包版（PyInstaller onefile）中 __file__ 位于临时解压目录，写入会被清空，
# 因此优先使用 Electron 注入的 MLS_USER_DATA（用户数据目录），仅开发时回退到 backend 目录。
def get_data_dir():
    ud = os.environ.get('MLS_USER_DATA', '')
    if ud and os.path.isdir(ud):
        return ud
    # 开发模式：backend 目录（与原有行为一致）
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

PRESET_FILE = os.path.join(get_data_dir(), "presets.json")


def load_presets():
    """加载所有预设"""
    if not os.path.exists(PRESET_FILE):
        return {}
    with open(PRESET_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_presets(presets):
    """保存预设"""
    os.makedirs(os.path.dirname(PRESET_FILE), exist_ok=True)
    with open(PRESET_FILE, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)


class PresetItem(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str
    password: str


@router.get("/api/preset/list")
async def list_presets():
    """列出所有预设名称"""
    presets = load_presets()
    return {"names": list(presets.keys())}


@router.post("/api/preset/save")
async def save_preset(item: PresetItem):
    """保存预设（密码加密）"""
    presets = load_presets()
    if item.name in presets:
        # 可以覆盖
        pass
    presets[item.name] = {
        "host": item.host,
        "port": item.port,
        "username": item.username,
        "password": encrypt_password(item.password)  # 加密存储
    }
    save_presets(presets)
    return {"message": "保存成功"}


@router.get("/api/preset/load")
async def load_preset(name: str):
    """加载预设（密码解密）"""
    presets = load_presets()
    if name not in presets:
        raise HTTPException(status_code=404, detail="预设不存在")
    data = presets[name]
    data["password"] = decrypt_password(data["password"])
    return data


@router.delete("/api/preset/delete")
async def delete_preset(name: str):
    """删除预设"""
    presets = load_presets()
    if name not in presets:
        raise HTTPException(status_code=404, detail="预设不存在")
    del presets[name]
    save_presets(presets)
    return {"message": "删除成功"}
