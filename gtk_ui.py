# gtk_ui.py
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import os # 导入os模块

def show_gtk_message(parent, title, message, msg_type):
    if msg_type == 'question':
        dialog = Gtk.MessageDialog(
            transient_for=parent,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=title,
        )
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES
    else:
        msg_type_map = {
            'info': Gtk.MessageType.INFO,
            'error': Gtk.MessageType.ERROR,
        }
        dialog = Gtk.MessageDialog(
            transient_for=parent,
            flags=0,
            message_type=msg_type_map.get(msg_type, Gtk.MessageType.INFO),
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

class ConfigEditor(Gtk.Dialog):
    def __init__(self, parent, controller):
        super().__init__(title="Cloudflare API 配置", transient_for=parent, flags=0)
        self.controller = controller
        self.add_button("取消", Gtk.ResponseType.CANCEL)
        save_button = self.add_button("保存并连接", Gtk.ResponseType.OK)
        save_button.connect("clicked", self.on_save_clicked)

        self.set_modal(True)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_resizable(False)
        self.set_border_width(10)

        area = self.get_content_area()
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=10)
        area.add(grid)

        grid.attach(Gtk.Label(label="Cloudflare Email:", xalign=0), 0, 0, 1, 1)
        self.email_entry = Gtk.Entry(width_chars=45, hexpand=True)
        grid.attach(self.email_entry, 0, 1, 1, 1)

        grid.attach(Gtk.Label(label="Global API Key:", xalign=0), 0, 2, 1, 1)
        self.key_entry = Gtk.Entry(width_chars=45, visibility=False, hexpand=True)
        grid.attach(self.key_entry, 0, 3, 1, 1)

        self.status_label = Gtk.Label(hexpand=True, xalign=0)
        grid.attach(self.status_label, 0, 4, 1, 1)
        self.show_all()

    def on_save_clicked(self, widget):
        email = self.email_entry.get_text().strip()
        key = self.key_entry.get_text().strip()
        if not email or not key:
            self.show_status("邮箱和API Key均不能为空。", "red")
            return
        self.controller.test_and_save_config(email, key, self)

    def show_status(self, message, color):
        self.status_label.set_markup(f'<span foreground="{color}">{message}</span>')

    def is_active(self):
        return self.get_visible()

    def close_editor(self):
        self.destroy()

class RecordEditor(Gtk.Dialog):
    def __init__(self, parent, controller, record=None):
        super().__init__(title="添加/编辑 DNS 记录", transient_for=parent, flags=0)
        self.controller = controller
        self.record_id = record.get('id') if record else None
        self.add_button("取消", Gtk.ResponseType.CANCEL)
        ok_button = self.add_button("确认", Gtk.ResponseType.OK)
        ok_button.connect("clicked", self.on_ok_clicked)

        self.set_modal(True)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_border_width(10)

        area = self.get_content_area()
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=10)
        area.add(grid)

        grid.attach(Gtk.Label(label="记录类型:", xalign=0), 0, 0, 1, 1)
        self.type_combo = Gtk.ComboBoxText()
        for t in ["A", "AAAA", "CNAME", "TXT", "NS"]:
            self.type_combo.append_text(t)
        grid.attach(self.type_combo, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="主机名:", xalign=0), 0, 1, 1, 1)
        self.name_entry = Gtk.Entry(hexpand=True)
        grid.attach(self.name_entry, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="内容:", xalign=0), 0, 2, 1, 1)
        self.content_entry = Gtk.Entry(hexpand=True)
        grid.attach(self.content_entry, 1, 2, 1, 1)

        self.proxy_check = Gtk.CheckButton(label="开启Cloudflare代理 (CDN)")
        grid.attach(self.proxy_check, 0, 3, 2, 1)

        if record:
            self.type_combo.set_active_id(record.get('type', 'A'))
            self.name_entry.set_text(record.get('name', ''))
            self.content_entry.set_text(record.get('content', ''))
            self.proxy_check.set_active(record.get('proxied', False))
        else:
            self.type_combo.set_active(0)
            self.name_entry.set_text("@")

        self.show_all()

    def on_ok_clicked(self, widget):
        record_type = self.type_combo.get_active_text()
        content = self.content_entry.get().strip()
        
        # 仅当不是A或AAAA记录时，才强制内容不能为空
        if not content and record_type not in ['A', 'AAAA']:
            show_gtk_message(self, "输入错误", "内容不能为空", "error")
            return

        record_data = {
            "type": record_type,
            "name": self.name_entry.get_text().strip() or "@",
            "content": content,
            "proxied": self.proxy_check.get_active()
        }
        self.controller.add_or_update_record(record_data, self.record_id)
        self.destroy()

class AppUI(Gtk.ApplicationWindow):
    def __init__(self, application, controller):
        super().__init__(application=application)
        self.controller = controller
        self.set_title("Cloudflare DNS Manager")
        self.set_default_size(1200, 700)
        self.set_border_width(10)

        # 设置窗口图标
        icon_path = '' # 初始化icon_path
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, 'cloudflare-dns-manager.png')
            self.set_icon_from_file(icon_path)
        except Exception as e:
            print(f"错误：无法从路径 '{icon_path}' 加载GTK图标: {e}")

        main_pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, wide_handle=True)
        self.add(main_pane)

        # --- Left Pane ---
        left_grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL, row_spacing=5)
        main_pane.add1(left_grid)

        self.refresh_domains_button = Gtk.Button(label="刷新域名列表")
        self.refresh_domains_button.connect("clicked", lambda w: self.controller.load_domains())
        left_grid.attach(self.refresh_domains_button, 0, 0, 1, 1)

        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_grid.attach(scrolled_window, 0, 1, 1, 1)

        self.domain_listbox = Gtk.ListBox()
        self.domain_listbox.connect("row-selected", self.on_domain_row_selected)
        scrolled_window.add(self.domain_listbox)

        self.change_account_button = Gtk.Button(label="更改账户")
        self.change_account_button.connect("clicked", lambda w: self.controller.prompt_for_config())
        left_grid.attach(self.change_account_button, 0, 2, 1, 1)

        # --- Right Pane ---
        right_grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL, row_spacing=5)
        main_pane.add2(right_grid)

        top_bar = Gtk.Grid(column_spacing=10)
        right_grid.attach(top_bar, 0, 0, 1, 1)

        self.status_label = Gtk.Label(label="请从左侧选择一个域名", hexpand=True, xalign=0)
        top_bar.attach(self.status_label, 0, 0, 1, 1)

        button_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        top_bar.attach(button_container, 1, 0, 1, 1)

        self.add_button = Gtk.Button.new_with_label("添加新记录")
        self.add_button.connect("clicked", lambda w: self.controller.open_add_record_window())
        button_container.pack_start(self.add_button, False, False, 0)

        self.refresh_records_button = Gtk.Button.new_with_label("刷新记录")
        self.refresh_records_button.connect("clicked", lambda w: self.controller.refresh_current_records())
        button_container.pack_start(self.refresh_records_button, False, False, 0)

        self.delete_button = Gtk.Button.new_with_label("删除选中记录")
        self.delete_button.get_style_context().add_class("destructive-action")
        self.delete_button.connect("clicked", lambda w: self.controller.delete_selected_record())
        button_container.pack_start(self.delete_button, False, False, 0)

        scrolled_window_records = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scrolled_window_records.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        right_grid.attach(scrolled_window_records, 0, 1, 1, 1)

        self.records_store = Gtk.ListStore(str, str, str, str, str) # id, type, name, content, proxied
        self.records_tree = Gtk.TreeView(model=self.records_store)
        self.records_tree.get_selection().connect("changed", self.on_tree_selection_changed)
        scrolled_window_records.add(self.records_tree)

        columns = [("类型", 80), ("名称", 250), ("内容", 400), ("代理", 60)]
        for i, (title, width) in enumerate(columns):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i + 1)
            column.set_resizable(True)
            column.set_min_width(width)
            column.set_sort_column_id(i + 1)
            self.records_tree.append_column(column)

        self.clear_ui()
        self.show_all()

    def _setup_styles(self):
        css_provider = Gtk.CssProvider()
        css = b"""...""" # CSS from previous step
        css_provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def clear_ui(self):
        for child in self.domain_listbox.get_children():
            self.domain_listbox.remove(child)
        self.records_store.clear()
        self.set_record_buttons_state(False)

    def set_record_buttons_state(self, active):
        self.add_button.set_sensitive(active)
        self.refresh_records_button.set_sensitive(active)
        self.delete_button.set_sensitive(False)

    def set_delete_button_state(self, active):
        self.delete_button.set_sensitive(active)

    def update_domain_list(self, zones, error):
        self.clear_ui()
        if error:
            row = Gtk.ListBoxRow()
            row.add(Gtk.Label(label=f"加载失败: {error}"))
            self.domain_listbox.add(row)
        elif not zones:
            row = Gtk.ListBoxRow()
            row.add(Gtk.Label(label="未找到任何域名"))
            self.domain_listbox.add(row)
        else:
            for zone in zones:
                row = Gtk.ListBoxRow()
                row.add(Gtk.Label(label=zone['name']))
                self.domain_listbox.add(row)
        self.domain_listbox.show_all()

    def on_domain_row_selected(self, listbox, row):
        if row:
            self.controller.on_domain_selected(row.get_index())

    def show_loading_records(self):
        self.records_store.clear()
        self.records_store.append(["loading", "", "正在查询，请稍候...", "", ""])

    def update_dns_records_list(self, records, error):
        self.records_store.clear()
        if error:
            self.records_store.append(["error", "错误", f"加载记录失败: {error}", "", ""])
        elif not records:
            self.records_store.append(["empty", "", "该域名下没有解析记录。", "", ""])
        else:
            for r in records:
                self.records_store.append([r['id'], r['type'], r['name'], r['content'], "是" if r.get('proxied') else "否"])

    def on_tree_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        selection_exists = treeiter is not None and model[treeiter][0] not in ["empty", "error", "loading"]
        self.controller.on_record_selection_change(selection_exists)

    def get_selected_record_info(self):
        model, treeiter = self.records_tree.get_selection().get_selected()
        if treeiter is not None:
            record_id = model[treeiter][0]
            record_name = model[treeiter][2]
            return record_id, record_name
        return None, None

    def set_status_message(self, text):
        self.status_label.set_text(text)