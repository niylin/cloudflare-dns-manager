# cloudflare_api.py
import requests

class CloudflareAPI:
    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(self, email: str, api_key: str):
        if not email or not api_key:
            raise ValueError("API Key 和 Email 不能为空")
            
        self.headers = {
            "X-Auth-Email": email,
            "X-Auth-Key": api_key,
            "Content-Type": "application/json"
        }

    def _request(self, method, endpoint, **kwargs):
        """通用请求处理"""
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status() # 如果状态码不是 2xx，则抛出异常
            return response.json(), None
        except requests.exceptions.RequestException as e:
            # 尝试解析错误响应
            try:
                error_detail = e.response.json()['errors'][0]['message']
            except (AttributeError, KeyError, IndexError, TypeError):
                error_detail = str(e)
            return None, f"API 请求失败: {error_detail}"

    def get_zones(self):
        """获取所有可用域名区域"""
        data, error = self._request("get", "zones")
        return (data['result'], error) if data else (None, error)

    def get_dns_records(self, zone_id: str):
        """获取指定区域的 DNS 记录"""
        data, error = self._request("get", f"zones/{zone_id}/dns_records")
        return (data['result'], error) if data else (None, error)

    def add_dns_record(self, zone_id: str, record_type: str, name: str, content: str, proxied: bool = False, ttl: int = 1):
        """添加一条 DNS 记录"""
        payload = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied
        }
        data, error = self._request("post", f"zones/{zone_id}/dns_records", json=payload)
        return (data, error)

    def delete_dns_record(self, zone_id: str, record_id: str):
        """删除一条 DNS 记录"""
        return self._request("delete", f"zones/{zone_id}/dns_records/{record_id}")
        
    