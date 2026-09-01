import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 密钥文件路径（存储加密密钥）
KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".mls_key")


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
