# app_controller.py
import tkinter as tk
from tkinter import messagebox
import threading
import queue
from cloudflare_api import CloudflareAPI
import config_loader
from app_ui import AppUI, RecordEditor, ConfigEditor

class AppController:
    def __init__(self, root):
        self.root = root
        self.api = None
        self.zones = []
        self.current_zone = None
        self.dns_cache = {}
        self.callback_queue = queue.Queue()
        self.ui = AppUI(root, self)
        self.initialize_app()
        self.process_queue()

    def process_queue(self):
        try:
            callback, kwargs = self.callback_queue.get_nowait()
            callback(**kwargs)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def threaded_task(self, task_func, callback_func, callback_kwargs=None):
        if callback_kwargs is None:
            callback_kwargs = {}
        def worker():
            result, error = task_func()
            final_kwargs = {"result": result, "error": error, **callback_kwargs}
            self.callback_queue.put((callback_func, final_kwargs))
        threading.Thread(target=worker, daemon=True).start()

    def initialize_app(self):
        # 清理旧UI状态
        self.ui.clear_dns_records_list()
        self.ui.domain_listbox.delete(0, tk.END)
        self.ui.set_record_buttons_state("disabled")
        
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
        self.ui.set_status_message("请输入您的Cloudflare API信息")
        ConfigEditor(self.root, self)

    def test_and_save_config(self, email, key, editor_window):
        editor_window.show_status("正在验证凭据...", "blue")
        temp_api = CloudflareAPI(email, key)
        self.threaded_task(
            task_func=temp_api.get_zones,
            callback_func=self._on_config_test_done,
            callback_kwargs={"email": email, "key": key, "editor_window": editor_window}
        )

    def _on_config_test_done(self, result, error, email, key, editor_window):
        if not editor_window.winfo_exists():
            return

        if error:
            editor_window.show_status(f"连接失败: {error}", "red")
        else:
            config_loader.save_config(email, key)
            editor_window.destroy()
            self.ui.set_status_message("凭据验证成功，正在加载数据...")
            self.initialize_app() # 重新初始化以加载新账户

    def load_domains(self):
        if not self.api: return
        self.ui.set_status_message("正在加载域名...")
        self.dns_cache.clear()
        self.threaded_task(self.api.get_zones, self._update_domain_list_callback)

    def _update_domain_list_callback(self, result, error, **kwargs):
        self.zones = result if not error else []
        self.ui.update_domain_list(self.zones, error)
        if not error:
            self.ui.set_status_message("请从左侧选择一个域名")
        else:
            self.ui.set_status_message(f"加载域名失败: {error}")

    def on_domain_select(self, event):
        selection_indices = self.ui.domain_listbox.curselection()
        if not selection_indices: return
        selected_index = selection_indices[0]
        if not self.zones or selected_index >= len(self.zones): return

        zone = self.zones[selected_index]
        self.current_zone = zone
        self.ui.set_status_message(f"当前域名: {zone['name']}")
        self.ui.set_record_buttons_state("normal") # 启用添加和刷新按钮

        if zone['id'] in self.dns_cache:
            self.ui.update_dns_records_list(self.dns_cache[zone['id']], None)
        else:
            self.refresh_current_records()

    def _handle_api_dns_response(self, result, error, **kwargs):
        if not error and self.current_zone:
            self.dns_cache[self.current_zone['id']] = result
        self.ui.update_dns_records_list(result, error)
        
    def open_add_record_window(self):
        if self.current_zone: RecordEditor(self.root, self)

    def add_new_record(self, record_data):
        if not self.current_zone: return
        name = self.current_zone['name'] if record_data['name'] == '@' else f"{record_data['name']}.{self.current_zone['name']}"
        task_func = lambda: self.api.add_dns_record(
            zone_id=self.current_zone['id'], record_type=record_data['type'],
            name=name, content=record_data['content'], proxied=record_data['proxied'])
        self.threaded_task(task_func, self._handle_modify_response)
        
    def refresh_current_records(self):
        """修改: _refresh_current_records 变为公有方法供按钮调用"""
        if not self.current_zone:
            return

        zone_id = self.current_zone['id']
        if zone_id in self.dns_cache:
            del self.dns_cache[zone_id]

        self.ui.show_loading_records()
        self.threaded_task(lambda: self.api.get_dns_records(zone_id), self._handle_api_dns_response)

    def _handle_modify_response(self, result, error, **kwargs):
        if error:
            messagebox.showerror("操作失败", f"发生错误: {error}")
        else:
            messagebox.showinfo("操作成功", "DNS记录已更新。")
            self.refresh_current_records()

    def on_record_selection_change(self, event):
        if self.ui.records_tree.selection():
            selected_id = self.ui.records_tree.selection()[0]
            if selected_id in ["empty", "error", "loading"]:
                self.ui.delete_button.config(state="disabled")
            else:
                self.ui.delete_button.config(state="normal")
        else:
            self.ui.delete_button.config(state="disabled")
            
    def delete_selected_record(self):
        selected_ids = self.ui.records_tree.selection()
        if not selected_ids: return
        
        record_id = selected_ids[0]
        if record_id in ["empty", "error", "loading"]: return
        
        item = self.ui.records_tree.item(record_id)
        record_name = item['values'][1]

        if messagebox.askyesno("确认删除", f"您确定要永久删除记录 '{record_name}' 吗？\n此操作无法撤销。"):
            task_func = lambda: self.api.delete_dns_record(zone_id=self.current_zone['id'], record_id=record_id)
            self.threaded_task(task_func, self._handle_modify_response)