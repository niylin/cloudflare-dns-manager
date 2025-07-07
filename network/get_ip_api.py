# utils.py
import requests

def get_public_ip(version='v4'):
    """获取本机的公网 IP 地址，支持v4和v6，并增加备用API。"""
    
    # 定义一组API端点，每个都包含v4和v6的URL，并指定其返回类型
    api_endpoints = [
        {'name': 'ping0.cc', 'v4': 'https://ipv4.ping0.cc', 'v6': 'https://ipv6.ping0.cc', 'type': 'text'},
        {'name': 'ipinfo.io', 'v4': 'https://ipinfo.io/json', 'v6': 'https://v6.ipinfo.io/json', 'type': 'json'},
        {'name': 'ipify.org', 'v4': 'https://api.ipify.org?format=json', 'v6': 'https://api64.ipify.org?format=json', 'type': 'json'}
    ]

    for api in api_endpoints:
        url = api.get(version)
        if not url:
            continue

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            ip = None
            if api['type'] == 'text':
                ip = response.text.strip()
            elif api['type'] == 'json':
                data = response.json()
                ip = data.get('ip') or data.get('origin')
            
            if ip:
                # 如果是 httpbin.org (或其他可能返回多个IP的)，取第一个
                return ip.split(',')[0].strip(), None

        except requests.RequestException:
            # 如果一个API失败，继续尝试下一个
            continue

    # 如果所有API都失败了
    return None, f"获取公网IP({version})失败: 所有API均无响应或返回错误。"
