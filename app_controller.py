# app_controller.py
import threading
import queue
from cloudflare_api import CloudflareAPI
import config_loader
from utils import get_public_ip

# --- 全局变量，用于动态UI模块导入 ---
UI_MODULE = None
MESSAGE_BOX = None
IS_GTK = False

class AppController:
    def __init__(self, root, ui_type='tkinter'):
        self.root = root
        self.ui_type = ui_type
        self.api = None
        self.zones = []
        self.current_zone = None
        self.dns_cache = {}
        self.callback_queue = queue.Queue()
        self.ui = None

        self._load_ui_module()

        if IS_GTK:
            # 对于GTK, root是Gtk.Application, UI在 'activate'信号时创建
            self.root.connect('activate', self._activate_gtk_app)
        else:
            # 对于Tkinter, root是tk.Tk(), 立即创建UI
            self.ui = UI_MODULE.AppUI(self.root, self)
            self.initialize_app()
            self.process_queue()

    def _load_ui_module(self):
        global UI_MODULE, MESSAGE_BOX, IS_GTK
        if self.ui_type == 'gtk':
            import gtk_ui
            UI_MODULE = gtk_ui
            IS_GTK = True
        else:
            import app_ui
            from tkinter import messagebox
            UI_MODULE = app_ui
            MESSAGE_BOX = messagebox

    def _activate_gtk_app(self, app):
        # GTK应用的激活回调
        self.ui = UI_MODULE.AppUI(app, self)
        self.initialize_app()
        self.process_queue()

    def get_main_window(self):
        # 返回顶层窗口对象
        return self.ui if IS_GTK else self.root

    def process_queue(self):
        try:
            callback, kwargs = self.callback_queue.get_nowait()
            callback(**kwargs)
        except queue.Empty:
            pass
        finally:
            if IS_GTK:
                from gi.repository import GLib
                GLib.timeout_add(100, self.process_queue)
            else:
                self.root.after(100, self.process_queue)

    def threaded_task(self, task_func, callback_func, callback_kwargs=None):
        # 在后台线程中执行任务
        if callback_kwargs is None:
            callback_kwargs = {}
        def worker():
            result, error = task_func()
            final_kwargs = {"result": result, "error": error, **callback_kwargs}
            self.callback_queue.put((callback_func, final_kwargs))
        threading.Thread(target=worker, daemon=True).start()

    def initialize_app(self):
        # 初始化或重置应用状态
        self.ui.clear_ui()
        email, key = config_loader.load_config()
        if email and key:
            try:
                self.api = CloudflareAPI(email, key)
                self.load_domains()
            except ValueError as e:
                self.ui.set_status_message(f"错误: {e}")
                self.prompt_for_config()
        else:
            self.prompt_for_config()

    def prompt_for_config(self):
        # 弹出API配置窗口
        self.ui.set_status_message("请输入您的Cloudflare API信息")
        UI_MODULE.ConfigEditor(self.get_main_window(), self)

    def test_and_save_config(self, email, key, editor_window):
        # 测试并保存API配置
        editor_window.show_status("正在验证凭据...", "blue")
        temp_api = CloudflareAPI(email, key)
        self.threaded_task(
            task_func=temp_api.get_zones,
            callback_func=self._on_config_test_done,
            callback_kwargs={"email": email, "key": key, "editor_window": editor_window}
        )

    def _on_config_test_done(self, result, error, email, key, editor_window):
        # 配置测试完成后的回调
        if not editor_window.is_active(): return
        if error:
            editor_window.show_status(f"连接失败: {error}", "red")
        else:
            config_loader.save_config(email, key)
            editor_window.close_editor()
            self.ui.set_status_message("凭据验证成功，正在加载数据...")
            self.initialize_app()

    def load_domains(self):
        # 加载域名列表
        if not self.api: return
        self.ui.set_status_message("正在加载域名...")
        self.dns_cache.clear()
        self.threaded_task(self.api.get_zones, self._update_domain_list_callback)

    def _update_domain_list_callback(self, result, error, **kwargs):
        self.zones = result if not error else []
        self.ui.update_domain_list(self.zones, error)
        self.ui.set_status_message("请从左侧选择一个域名" if not error else f"加载域名失败: {error}")

    def on_domain_selected(self, selected_index):
        # 处理域名选择事件
        if not self.zones or selected_index >= len(self.zones): return
        zone = self.zones[selected_index]
        self.current_zone = zone
        self.ui.set_status_message(f"当前域名: {zone['name']}")
        self.ui.set_record_buttons_state(True)
        if zone['id'] in self.dns_cache:
            self.ui.update_dns_records_list(self.dns_cache[zone['id']], None)
        else:
            self.refresh_current_records()

    def refresh_current_records(self):
        # 刷新当前域名的DNS记录
        if not self.current_zone: return
        zone_id = self.current_zone['id']
        if zone_id in self.dns_cache: del self.dns_cache[zone_id]
        self.ui.show_loading_records()
        self.threaded_task(lambda: self.api.get_dns_records(zone_id), self._handle_api_dns_response)

    def _handle_api_dns_response(self, result, error, **kwargs):
        if not error and self.current_zone:
            self.dns_cache[self.current_zone['id']] = result
        self.ui.update_dns_records_list(result, error)

    def open_add_record_window(self):
        # 打开添加记录的窗口
        if self.current_zone:
            UI_MODULE.RecordEditor(self.get_main_window(), self)

    def add_or_update_record(self, record_data, record_id=None):
        # 添加或更新DNS记录
        if not self.current_zone: return

        record_type = record_data['type']
        # 如果是A或AAAA记录且内容为空，则获取公网IP
        if record_type in ['A', 'AAAA'] and not record_data['content']:
            ip_version = 'v6' if record_type == 'AAAA' else 'v4'
            self.ui.set_status_message(f"正在获取本机公网IP({ip_version})...")
            
            def get_ip_task(): # 定义一个标准的内部函数
                return get_public_ip(version=ip_version)

            self.threaded_task(
                task_func=get_ip_task, # 使用这个新函数
                callback_func=self._on_public_ip_fetched,
                callback_kwargs={"record_data": record_data, "record_id": record_id}
            )
            return

        self._execute_add_or_update(record_data, record_id)

    def _on_public_ip_fetched(self, result, error, record_data, record_id):
        if error:
            self.show_message("获取IP失败", error, "error")
            self.ui.set_status_message("获取公网IP失败")
            return
        
        record_data['content'] = result
        self.ui.set_status_message(f"已获取IP: {result}，正在添加记录...")
        self._execute_add_or_update(record_data, record_id)

    def _execute_add_or_update(self, record_data, record_id):
        # 核心的记录添加/更新逻辑
        name = self.current_zone['name'] if record_data['name'] == '@' else f"{record_data['name']}.{self.current_zone['name']}"
        
        if record_id: # 更新逻辑 (未来实现)
            # task_func = lambda: self.api.update_dns_record(...)
            pass
        else: # 添加逻辑
            task_func = lambda: self.api.add_dns_record(
                zone_id=self.current_zone['id'], record_type=record_data['type'],
                name=name, content=record_data['content'], proxied=record_data['proxied'])
            
        self.threaded_task(task_func, self._handle_modify_response)

    def on_record_selection_change(self, selection_exists):
        # 当DNS记录的选择状态改变时调用
        self.ui.set_delete_button_state(selection_exists)

    def delete_selected_record(self):
        # 删除选中的DNS记录
        record_id, record_name = self.ui.get_selected_record_info()
        if not record_id: return

        if self.show_confirmation("确认删除", f"您确定要永久删除记录 '{record_name}' 吗？\n此操作无法撤销。"):
            task_func = lambda: self.api.delete_dns_record(zone_id=self.current_zone['id'], record_id=record_id)
            self.threaded_task(task_func, self._handle_modify_response)

    def _handle_modify_response(self, result, error, **kwargs):
        # 处理添加/删除/更新API调用后的响应
        if error:
            self.show_message("操作失败", f"发生错误: {error}", "error")
        else:
            self.show_message("操作成功", "DNS记录已更新。", "info")
            self.refresh_current_records()

    def show_message(self, title, message, msg_type='info'):
        # 显示信息/错误对话框
        if IS_GTK:
            UI_MODULE.show_gtk_message(self.get_main_window(), title, message, msg_type)
        else:
            if msg_type == 'error': MESSAGE_BOX.showerror(title, message)
            else: MESSAGE_BOX.showinfo(title, message)

    def show_confirmation(self, title, message):
        # 显示确认对话框
        if IS_GTK:
            return UI_MODULE.show_gtk_message(self.get_main_window(), title, message, "question")
        else:
            return MESSAGE_BOX.askyesno(title, message)
