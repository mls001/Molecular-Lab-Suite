import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 密钥文件路径（存储加密密钥）
# 打包版中 __file__ 指向 PyInstaller 临时解压目录（退出即清空），必须写到持久目录：
# 优先 Electron 注入的 MLS_USER_DATA，开发模式回退 backend 目录。
def _data_dir():
    ud = os.environ.get('MLS_USER_DATA', '')
    if ud and os.path.isdir(ud):
        return ud
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

KEY_FILE = os.path.join(_data_dir(), ".mls_key")


def get_or_create_key():
    """获取或创建加密密钥"""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        # 生成新密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'mls_salt_fixed',  # 固定盐，实际可随机但需保存，此处简化
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(b"mls_secret_key"))  # 固定密码，可更改
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key


def encrypt_password(password: str) -> str:
    """加密密码"""
    key = get_or_create_key()
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """解密密码"""
    key = get_or_create_key()
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()
