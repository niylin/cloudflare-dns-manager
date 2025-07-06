# config_loader.py
import os
import json
import base64
import hashlib
import getpass
import uuid

# 定义配置文件路径
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'cfconfig')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'test_cfkey.json')

class Encryptor:

    def __init__(self):
        #  生成一个稳定且唯一的密钥，基于用户名和机器硬件ID
        try:
            # getpass.getuser() 在多种环境下更稳定
            user_id = getpass.getuser()
        except Exception:
            # 作为备用方案
            user_id = str(os.getuid()) if hasattr(os, 'getuid') else 'defaultuser'
        
        # uuid.getnode() 返回硬件地址 (MAC address)
        machine_id = str(uuid.getnode())
        
        # 将这些信息组合并用SHA256哈希，生成一个32字节的密钥
        secret_string = f"cf-dns-manager-{user_id}-{machine_id}-stable-secret"
        self.key = hashlib.sha256(secret_string.encode()).digest()

    def _xor_cipher(self, data: bytes) -> bytes:
        """核心的XOR加密/解密逻辑"""
        key_len = len(self.key)
        return bytes([b ^ self.key[i % key_len] for i, b in enumerate(data)])

    def encrypt(self, plaintext: str) -> str:
        """加密字符串并返回Base64编码的结果"""
        if not plaintext:
            return ""
        # 字符串转字节 -> XOR加密 -> Base64编码 -> 转回字符串
        encrypted_bytes = self._xor_cipher(plaintext.encode('utf-8'))
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """解密经过Base64编码的字符串"""
        if not ciphertext:
            return ""
        # 字符串转字节 -> Base64解码 -> XOR解密 -> 转回字符串
        decoded_bytes = base64.b64decode(ciphertext.encode('utf-8'))
        return self._xor_cipher(decoded_bytes).decode('utf-8')

# 创建一个全局的加密器实例
_encryptor = Encryptor()

def load_config():

    if not os.path.exists(CONFIG_PATH):
        return None, None
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
        
        # 从文件中获取加密后的数据
        encrypted_email = config_data.get("CF_Email_Encrypted")
        encrypted_api_key = config_data.get("CF_Key_Encrypted")
        
        if not encrypted_email or not encrypted_api_key:
            return None, None
        
        # 解密数据
        email = _encryptor.decrypt(encrypted_email)
        api_key = _encryptor.decrypt(encrypted_api_key)
            
        return email, api_key
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        # 任何解析、解码、解密错误都视为配置无效
        print(f"配置文件加载或解密失败: {e}")
        return None, None

def save_config(email: str, api_key: str):

    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # 在保存前加密数据
        config_data = {
            "CF_Email_Encrypted": _encryptor.encrypt(email),
            "CF_Key_Encrypted": _encryptor.encrypt(api_key)
        }
        
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True, "配置已成功加密并保存！"
    except Exception as e:
        return False, f"保存配置失败: {e}"