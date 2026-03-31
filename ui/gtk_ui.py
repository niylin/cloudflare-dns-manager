# gtk_ui.py
import gi
import os
import threading

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Gio, Adw, GLib, Pango

def show_gtk_message(parent, title, message, msg_type):
    # GTK 4 dialogs are non-blocking. We use an iteration loop to emulate synchronous behavior.
    result = {'response': None}

    alert = Adw.AlertDialog.new(title, message)
    
    if msg_type == 'question':
        alert.add_response("no", "取消")
        alert.add_response("yes", "确认")
        alert.set_default_response("no")
        alert.set_close_response("no")
    else:
        alert.add_response("ok", "确认")
        alert.set_default_response("ok")
        alert.set_close_response("ok")

    def on_response(dialog, res, data):
        result['response'] = dialog.choose_finish(res)

    alert.choose(parent, None, on_response, None)

    # Process events until we have a response
    while result['response'] is None:
        GLib.MainContext.default().iteration(True)

    return result['response'] in ["yes", "ok"]

class ConfigEditor(Adw.Window):
    def __init__(self, parent, controller):
        super().__init__(transient_for=parent, modal=True)
        self.controller = controller
        self.set_title("Cloudflare API 配置")
        self.set_default_size(400, -1)
        self.set_resizable(False)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content)

        header = Adw.HeaderBar()
        content.append(header)

        page = Adw.PreferencesPage()
        content.append(page)

        group = Adw.PreferencesGroup()
        page.add(group)

        self.email_row = Adw.EntryRow(title="Cloudflare Email")
        group.add(self.email_row)

        self.key_row = Adw.PasswordEntryRow(title="Global API Key")
        group.add(self.key_row)

        self.status_label = Gtk.Label(margin_top=10, margin_bottom=10)
        self.status_label.set_use_markup(True)
        group.add(self.status_label)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_start=20, margin_end=20, margin_bottom=20)
        button_box.set_halign(Gtk.Align.CENTER)
        content.append(button_box)

        cancel_btn = Gtk.Button(label="取消")
        cancel_btn.connect("clicked", lambda w: self.close())
        button_box.append(cancel_btn)

        save_btn = Gtk.Button(label="保存并连接")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self.on_save_clicked)
        button_box.append(save_btn)

        self.present()

    def on_save_clicked(self, widget):
        email = self.email_row.get_text().strip()
        key = self.key_row.get_text().strip()
        if not email or not key:
            self.show_status("邮箱和API Key均不能为空。", "red")
            return
        self.controller.test_and_save_config(email, key, self)

    def show_status(self, message, color):
        self.status_label.set_markup(f'<span foreground="{color}">{message}</span>')

    def is_active(self):
        return self.get_visible()

    def close_editor(self):
        self.close()

class RecordEditor(Adw.Window):
    def __init__(self, parent, controller, record=None):
        super().__init__(transient_for=parent, modal=True)
        self.controller = controller
        self.record_id = record.get('id') if record else None
        self.set_title("添加/编辑 DNS 记录")
        self.set_default_size(450, -1)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content)

        header = Adw.HeaderBar()
        content.append(header)

        page = Adw.PreferencesPage()
        content.append(page)

        group = Adw.PreferencesGroup()
        page.add(group)

        self.type_row = Adw.ComboRow(title="记录类型")
        self.type_model = Gtk.StringList.new(["A", "AAAA", "CNAME", "TXT", "NS"])
        self.type_row.set_model(self.type_model)
        group.add(self.type_row)

        self.name_row = Adw.EntryRow(title="主机名")
        group.add(self.name_row)

        self.content_row = Adw.EntryRow(title="内容")
        group.add(self.content_row)

        self.proxy_row = Adw.SwitchRow(title="开启Cloudflare代理 (CDN)")
        group.add(self.proxy_row)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_start=20, margin_end=20, margin_bottom=20)
        button_box.set_halign(Gtk.Align.CENTER)
        content.append(button_box)

        cancel_btn = Gtk.Button(label="取消")
        cancel_btn.connect("clicked", lambda w: self.close())
        button_box.append(cancel_btn)

        ok_btn = Gtk.Button(label="确认")
        ok_btn.add_css_class("suggested-action")
        ok_btn.connect("clicked", self.on_ok_clicked)
        button_box.append(ok_btn)

        if record:
            # Set record values
            type_idx = ["A", "AAAA", "CNAME", "TXT", "NS"].index(record.get('type', 'A'))
            self.type_row.set_selected(type_idx)
            self.name_row.set_text(record.get('name', ''))
            self.content_row.set_text(record.get('content', ''))
            self.proxy_row.set_active(record.get('proxied', False))
        else:
            self.type_row.set_selected(0)
            self.name_row.set_text("@")

        self.present()

    def on_ok_clicked(self, widget):
        record_type = self.type_model.get_string(self.type_row.get_selected())
        content = self.content_row.get_text().strip()
        
        if not content and record_type not in ['A', 'AAAA']:
            show_gtk_message(self, "输入错误", "内容不能为空", "error")
            return

        record_data = {
            "type": record_type,
            "name": self.name_row.get_text().strip() or "@",
            "content": content,
            "proxied": self.proxy_row.get_active()
        }
        self.controller.add_or_update_record(record_data, self.record_id)
        self.close()

class AppUI(Adw.ApplicationWindow):
    def __init__(self, application, controller):
        super().__init__(application=application)
        self.controller = controller
        self.set_title("Cloudflare DNS Manager")
        self.set_default_size(1200, 700)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header Bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Main Paned
        main_pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, wide_handle=True)
        main_box.append(main_pane)

        # --- Left Pane (Domains) ---
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        main_pane.set_start_child(left_box)

        self.refresh_domains_button = Gtk.Button(label="刷新域名列表")
        self.refresh_domains_button.connect("clicked", lambda w: self.controller.load_domains())
        left_box.append(self.refresh_domains_button)

        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_box.append(scrolled_window)

        self.domain_listbox = Gtk.ListBox()
        self.domain_listbox.add_css_class("navigation-sidebar")
        self.domain_listbox.connect("row-selected", self.on_domain_row_selected)
        scrolled_window.set_child(self.domain_listbox)

        # Context menu for domains
        self.domain_popover = Gtk.PopoverMenu.new_from_model(None)
        self.domain_popover.set_parent(self.domain_listbox)
        self.domain_popover.set_has_arrow(True)
        domain_menu = Gio.Menu.new()
        domain_menu.append("复制域名", "win.copy_domain")
        self.domain_popover.set_menu_model(domain_menu)

        domain_gesture = Gtk.GestureClick.new()
        domain_gesture.set_button(Gdk.BUTTON_SECONDARY)
        domain_gesture.connect("pressed", self.on_domain_right_click)
        self.domain_listbox.add_controller(domain_gesture)

        self.change_account_button = Gtk.Button(label="更改账户")
        self.change_account_button.connect("clicked", lambda w: self.controller.prompt_for_config())
        left_box.append(self.change_account_button)

        # --- Right Pane (Records) ---
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        main_pane.set_end_child(right_box)

        top_bar = Gtk.CenterBox()
        right_box.append(top_bar)

        self.status_label = Gtk.Label(label="请从左侧选择一个域名", xalign=0)
        self.status_label.add_css_class("heading")
        top_bar.set_start_widget(self.status_label)

        button_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        top_bar.set_end_widget(button_container)

        self.add_button = Gtk.Button(label="添加新记录")
        self.add_button.connect("clicked", lambda w: self.controller.open_add_record_window())
        button_container.append(self.add_button)

        self.refresh_records_button = Gtk.Button(label="刷新记录")
        self.refresh_records_button.connect("clicked", lambda w: self.controller.refresh_current_records())
        button_container.append(self.refresh_records_button)

        self.delete_button = Gtk.Button(label="删除选中记录")
        self.delete_button.add_css_class("destructive-action")
        self.delete_button.connect("clicked", lambda w: self.controller.delete_selected_record())
        button_container.append(self.delete_button)

        scrolled_window_records = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scrolled_window_records.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        right_box.append(scrolled_window_records)

        self.records_store = Gtk.ListStore(str, str, str, str, str) # id, type, name, content, proxied
        self.records_tree = Gtk.TreeView(model=self.records_store)
        self.records_tree.get_selection().connect("changed", self.on_tree_selection_changed)
        scrolled_window_records.set_child(self.records_tree)

        # Context menu for records
        self.records_popover = Gtk.PopoverMenu.new_from_model(None)
        self.records_popover.set_parent(self.records_tree)
        self.records_popover.set_has_arrow(True)
        records_menu = Gio.Menu.new()
        records_menu.append("复制名称", "win.copy_name")
        records_menu.append("复制内容", "win.copy_content")
        self.records_popover.set_menu_model(records_menu)

        records_gesture = Gtk.GestureClick.new()
        records_gesture.set_button(Gdk.BUTTON_SECONDARY)
        records_gesture.connect("pressed", self.on_records_right_click)
        self.records_tree.add_controller(records_gesture)

        # Actions for copying
        self.add_action_with_callback("copy_domain", self.on_copy_domain)
        self.add_action_with_callback("copy_name", self.on_copy_name)
        self.add_action_with_callback("copy_content", self.on_copy_content)

        columns = [("类型", 60, False), ("名称", 150, True), ("内容", 200, True), ("代理", 60, False)]
        for i, (title, width, expand) in enumerate(columns):
            renderer = Gtk.CellRendererText()
            renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn(title, renderer, text=i + 1)
            column.set_resizable(True)
            column.set_expand(expand)
            column.set_min_width(width)
            column.set_sort_column_id(i + 1)
            self.records_tree.append_column(column)

        self.clear_ui()
        self.present()

    def add_action_with_callback(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

    def on_domain_right_click(self, gesture, n_press, x, y):
        row = self.domain_listbox.get_row_at_y(int(y))
        if row:
            self.domain_listbox.select_row(row)
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
            self.domain_popover.set_pointing_to(rect)
            self.domain_popover.popup()

    def on_records_right_click(self, gesture, n_press, x, y):
        path_info = self.records_tree.get_path_at_pos(int(x), int(y))
        if path_info:
            path, col, cell_x, cell_y = path_info
            self.records_tree.get_selection().select_path(path)
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
            self.records_popover.set_pointing_to(rect)
            self.records_popover.popup()

    def on_copy_domain(self, action, param):
        row = self.domain_listbox.get_selected_row()
        if row:
            # AdwActionRow title
            self.get_display().get_clipboard().set(row.get_title())

    def on_copy_name(self, action, param):
        _, record_name = self.get_selected_record_info()
        if record_name:
            self.get_display().get_clipboard().set(record_name)

    def on_copy_content(self, action, param):
        model, treeiter = self.records_tree.get_selection().get_selected()
        if treeiter:
            content = model[treeiter][3]
            self.get_display().get_clipboard().set(content)

    def clear_ui(self):
        # Only remove ListBoxRow children to avoid removing popovers or other internal widgets
        child = self.domain_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            if isinstance(child, Gtk.ListBoxRow):
                self.domain_listbox.remove(child)
            child = next_child
            
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
            row = Adw.ActionRow(title=f"加载失败: {error}")
            self.domain_listbox.append(row)
        elif not zones:
            row = Adw.ActionRow(title="未找到任何域名")
            self.domain_listbox.append(row)
        else:
            for zone in zones:
                row = Adw.ActionRow(title=zone['name'])
                self.domain_listbox.append(row)

    def on_domain_row_selected(self, listbox, row):
        if row:
            # We need to find the index of the row
            idx = 0
            iter_row = listbox.get_first_child()
            while iter_row:
                if iter_row == row:
                    self.controller.on_domain_selected(idx)
                    break
                iter_row = iter_row.get_next_sibling()
                idx += 1

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
