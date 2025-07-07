#!/usr/bin/env python3

import os
import sys
import time
from colorama import Fore, Style, init
from config_loader import load_config, save_config
from network.cloudflare_api import CloudflareAPI
from network.get_ip_api import get_public_ip

init(autoreset=True)

def print_header(title=""):
    """清屏并打印统一的程序标题。"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Fore.CYAN}--- Cloudflare Dns Manager-CLI ---{Style.RESET_ALL}")
    if title:
        print(f"\n{title}")

def handle_error(message, sleep_duration=1.5):
    """打印错误消息并暂停。"""
    print(f"{Fore.RED}{message}")
    time.sleep(sleep_duration)

def main():
    """程序主入口。"""
    email, api_key = load_config()
    if not email or not api_key:
        print_header()
        print("未找到 Cloudflare 配置，让我们开始设置。")
        email = input("请输入您的 Cloudflare 邮箱地址: ").strip()
        api_key = input("请输入您的 Cloudflare Global API Key: ").strip()
        
        success, message = save_config(email, api_key)
        print(message)
        if not success:
            sys.exit(1)

    try:
        cf_api = CloudflareAPI(email=email, api_key=api_key)
    except ValueError as e:
        handle_error(f"错误: {e}")
        sys.exit(1)

    print("正在获取域名列表，请稍候...")
    zones, error = cf_api.get_zones()
    if error:
        handle_error(f"获取域名列表失败，无法继续操作: {error}")
        sys.exit(1)
    
    domain_list = [zone["name"] for zone in zones]

    while True:
        print_header("可供选择的域名列表, q退出：")
        for i, domain in enumerate(domain_list, start=1):
            print(f"{Fore.GREEN}{i}{Style.RESET_ALL}. {Fore.BLUE}{domain}{Style.RESET_ALL}")

        domain_choice = input("\n请输入选项编号： ")
        if domain_choice.lower() == 'q':
            print("退出脚本")
            break

        try:
            domain_index = int(domain_choice) - 1
            domain_name = domain_list[domain_index]
            zone_id = zones[domain_index]["id"]
            manage_domain_records(cf_api, domain_name, zone_id)
        except (ValueError, IndexError):
            continue

def manage_domain_records(cf_api: CloudflareAPI, domain_name: str, zone_id: str):
    """管理特定域名的 DNS 解析记录。"""
    records, error = cf_api.get_dns_records(zone_id)
    if error:
        handle_error(f"获取解析记录列表失败: {error}")
        return

    while True:
        title = f"您正在管理域名：{Fore.GREEN}{domain_name}{Style.RESET_ALL}"
        print_header(title)
        
        print("-----------------------\n当前解析记录列表：")
        if not records:
            print(f"{Fore.YELLOW}此域名下未找到任何解析记录。")
        else:
            for i, record in enumerate(records, start=1):
                proxy_status = f"({Fore.CYAN}代理开启{Style.RESET_ALL})" if record.get('proxied') else ""
                print(f"[{i}] {Fore.GREEN}{record['name']}{Style.RESET_ALL} ({Fore.YELLOW}{record['type']}{Style.RESET_ALL}) -> {Fore.BLUE}{record['content']}{Style.RESET_ALL} {proxy_status}")
        
        print("-----------------------\n1. 添加解析记录\n2. 删除解析记录\nq. 返回主域名列表\n-----------------------")
        main_choice = input("请输入选项编号： ")
        
        action_taken = False
        if main_choice == '1':
            action_taken = add_record_flow(cf_api, domain_name, zone_id)
        elif main_choice == '2':
            if not records:
                handle_error("当前没有可供删除的记录。")
                continue
            action_taken = delete_record_flow(cf_api, zone_id, records)
        elif main_choice.lower() == 'q':
            break
        else:
            handle_error("无效的选项")

        if action_taken:
            print("操作完成，正在刷新记录列表...")
            time.sleep(1)
            records, error = cf_api.get_dns_records(zone_id)
            if error:
                handle_error(f"刷新列表失败: {error}")
                break

def add_record_flow(cf_api: CloudflareAPI, domain_name: str, zone_id: str) -> bool:
    """引导用户添加一条新的 DNS 记录, 成功返回 True。"""
    print("\n--- 添加新记录 (输入 'q' 可随时取消) ---")
    
    record_types = {"1": "A", "2": "AAAA", "3": "CNAME", "4": "NS", "5": "TXT"}
    parsing_type = input("记录类型 (1: A, 2: AAAA, 3: CNAME, 4: NS, 5: TXT): ")
    if parsing_type.lower() == 'q': return False
    
    record_type = record_types.get(parsing_type)
    if not record_type:
        handle_error("无效的记录类型。")
        return False
    
    prefix_name = input(f"域名前缀 (解析主域名 {domain_name} 请留空): ").strip()
    if prefix_name.lower() == 'q': return False
    
    content = input(f"内容/IP地址 (输入 '+++' 获取本机公网IP): ").strip()
    if content.lower() == 'q': return False

    if content == "+++":
        ip_version = 'v6' if record_type == "AAAA" else 'v4'
        public_ip, error = get_public_ip(version=ip_version)
        if error:
            handle_error(error)
            return False
        content = public_ip
        print(f"已自动获取IP地址: {Fore.BLUE}{content}{Style.RESET_ALL}")

    proxied = False
    if record_type in ["A", "AAAA", "CNAME"]:
        cdn_choice = input("是否开启CDN代理 (1: 开启, 其他为不开启): ")
        if cdn_choice.lower() == 'q': return False
        proxied = (cdn_choice == "1")

    _, error = cf_api.add_dns_record(zone_id, record_type, prefix_name or domain_name, content, proxied)
    if error:
        handle_error(f"主机名解析添加失败: {error}")
        return False

    print(f"\n{Fore.GREEN}主机名解析成功！")
    return True

def delete_record_flow(cf_api: CloudflareAPI, zone_id: str, records: list) -> bool:
    """引导用户删除 DNS 记录, 成功返回 True。"""
    print("\n--- 删除记录 ---")
    prompt = f"输入记录编号删除单条, 输入 '{Fore.GREEN}Delete all parsing records{Style.RESET_ALL}' 删除全部, 或 'q' 取消: "
    user_input = input(prompt)

    if user_input.lower() == 'q':
        return False

    action_success = False
    if user_input == "Delete all parsing records":
        print(f"{Fore.YELLOW}正在删除全部 {len(records)} 条解析记录...")
        deleted_count = sum(1 for r in records if cf_api.delete_dns_record(zone_id, r['id'])[1] is None)
        if deleted_count > 0:
            action_success = True
        print(f"{Fore.GREEN}操作完成, 成功删除 {deleted_count} 条记录。")
    else:
        try:
            record_index = int(user_input) - 1
            record_to_delete = records[record_index]
            print(f"正在删除记录: {record_to_delete['name']} -> {record_to_delete['content']}...")
            _, err = cf_api.delete_dns_record(zone_id, record_to_delete['id'])
            if err:
                handle_error(f"删除记录失败: {err}")
            else:
                print(f"{Fore.GREEN}记录已成功删除。")
                action_success = True
        except (ValueError, IndexError):
            handle_error("无效的输入或编号。")
    
    time.sleep(1.5)
    return action_success

if __name__ == "__main__":
    main()