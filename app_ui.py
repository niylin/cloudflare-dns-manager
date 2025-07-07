# app_ui.py
import tkinter as tk
from tkinter import ttk

class ConfigEditor(tk.Toplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.title("Cloudflare API 配置")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        frame = ttk.Frame(self, padding="20")
        frame.pack(expand=True, fill="both")

        # --- 新增: 注册验证函数 ---
        # %P 代表 "如果编辑成功，输入框的文本内容将会是什么"
        # 我们用它来检查长度
        validate_cmd = (self.register(self._validate_length), '%P')

        # --- 修改: 为输入框添加验证 ---
        ttk.Label(frame, text="Cloudflare Email:").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.email_entry = ttk.Entry(
            frame,
            width=45,
            validate='key', # 在每次按键时验证
            validatecommand=(validate_cmd + ('255',)) # 传递最大长度255
        )
        self.email_entry.grid(row=1, column=0, pady=(0, 10))

        ttk.Label(frame, text="Global API Key:").grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.key_entry = ttk.Entry(
            frame,
            width=45,
            show="*",
            validate='key', # 在每次按键时验证
            validatecommand=(validate_cmd + ('100',)) # 传递最大长度100
        )
        self.key_entry.grid(row=3, column=0, pady=(0, 10))

        self.status_label = ttk.Label(frame, text="", wraplength=300)
        self.status_label.grid(row=4, column=0, pady=(5, 10))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0)
        
        self.save_button = ttk.Button(button_frame, text="保存并连接", command=self.save)
        self.save_button.pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=self.destroy).pack(side="left", padx=5)
        
        self.center_window(parent)
        self.email_entry.focus_set()

    def _validate_length(self, proposed_text, max_length_str):

        # 新增: 验证函数，确保输入文本的长度不超过最大值。

        max_length = int(max_length_str)
        # 如果长度有效，返回True；否则返回False，Tkinter将阻止此次输入。
        return len(proposed_text) <= max_length

    def center_window(self, parent):
        self.update_idletasks()
        parent_x, parent_y = parent.winfo_x(), parent.winfo_y()
        parent_w, parent_h = parent.winfo_width(), parent.winfo_height()
        my_w, my_h = self.winfo_width(), self.winfo_height()
        x_pos = parent_x + (parent_w // 2) - (my_w // 2)
        y_pos = parent_y + (parent_h // 2) - (my_h // 2)
        self.geometry(f"+{x_pos}+{y_pos}")

    def save(self):
        email = self.email_entry.get().strip()
        key = self.key_entry.get().strip()
        if not email or not key:
            self.show_status("邮箱和API Key均不能为空。", "red")
            return
        self.controller.test_and_save_config(email, key, self)

    def show_status(self, message, color):
        self.status_label.config(text=message, foreground=color)
        new_state = "disabled" if color != "red" else "normal"
        self.save_button.config(state=new_state)

    def is_active(self):
        return self.winfo_exists()

    def close_editor(self):
        self.destroy()


class RecordEditor(tk.Toplevel):
    # ... (此部分代码无变化)
    def __init__(self, parent, controller, record=None):
        super().__init__(parent)
        self.controller = controller
        self.record_id = record.get('id') if record else None
        self.title("添加/编辑 DNS 记录")
        self.transient(parent)
        self.grab_set()
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill="both")
        ttk.Label(frame, text="记录类型:").grid(row=0, column=0, sticky="w", pady=5)
        self.type_combo = ttk.Combobox(frame, values=["A", "AAAA", "CNAME", "TXT", "NS"], state="readonly")
        self.type_combo.grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Label(frame, text="主机名:").grid(row=1, column=0, sticky="w", pady=5)
        self.name_entry = ttk.Entry(frame)
        self.name_entry.grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Label(frame, text="内容:").grid(row=2, column=0, sticky="w", pady=5)
        self.content_entry = ttk.Entry(frame)
        self.content_entry.grid(row=2, column=1, sticky="ew", pady=5)
        self.proxy_var = tk.BooleanVar()
        self.proxy_check = ttk.Checkbutton(frame, text="开启Cloudflare代理 (CDN)", variable=self.proxy_var)
        self.proxy_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=10)
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="确认", command=self.submit).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=self.destroy).pack(side="left", padx=5)
        if record:
            self.type_combo.set(record.get('type', 'A'))
            self.name_entry.insert(0, record.get('name', ''))
            self.content_entry.insert(0, record.get('content', ''))
            self.proxy_var.set(record.get('proxied', False))
        else:
            self.type_combo.set("A")
            self.name_entry.insert(0, "@")
        frame.columnconfigure(1, weight=1)
        self.name_entry.focus()
    def submit(self):
        record_type = self.type_combo.get()
        content = self.content_entry.get().strip()
        name = self.name_entry.get().strip() or "@"

        if not content and record_type not in ['A', 'AAAA']:
            from tkinter import messagebox
            messagebox.showwarning("输入错误", "内容不能为空", parent=self)
            return

        record_data = {"type": record_type, "name": name, "content": content, "proxied": self.proxy_var.get()}
        self.controller.add_or_update_record(record_data, self.record_id)
        self.destroy()

class AppUI:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        
        main_pane = ttk.PanedWindow(root, orient="horizontal")
        main_pane.pack(expand=True, fill="both", padx=10, pady=10)

        # --- 左侧面板 ---
        left_frame = ttk.Frame(main_pane, padding=5)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1) # 让域名列表区域可伸缩
        main_pane.add(left_frame, weight=1)

        self.refresh_domains_button = ttk.Button(left_frame, text="刷新域名列表", command=self.controller.load_domains)
        self.refresh_domains_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        list_frame = ttk.Frame(left_frame)
        list_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.domain_listbox = tk.Listbox(list_frame, bg="#333333", fg="white", borderwidth=0, highlightthickness=0, selectbackground="#094771")
        self.domain_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.domain_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.domain_listbox.config(yscrollcommand=scrollbar.set)
        self.domain_listbox.bind("<<ListboxSelect>>", self._on_domain_select_event)

        self.change_account_button = ttk.Button(left_frame, text="更改账户", command=self.controller.prompt_for_config)
        self.change_account_button.grid(row=2, column=0, padx=5, pady=(0, 5), sticky="ew")


        # --- 右侧面板 ---
        right_frame = ttk.Frame(main_pane, padding=5)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        main_pane.add(right_frame, weight=3)

        top_bar = ttk.Frame(right_frame)
        top_bar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        top_bar.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(top_bar, text="请从左侧选择一个域名", font=("sans-serif", 12, "bold"))
        self.status_label.grid(row=0, column=0, sticky="w")
        
        button_container = ttk.Frame(top_bar)
        button_container.grid(row=0, column=1, sticky="e")
        
        self.add_button = ttk.Button(button_container, text="添加新记录", state="disabled", command=self.controller.open_add_record_window)
        self.add_button.pack(side="left", padx=(0, 5))
        
        self.refresh_records_button = ttk.Button(button_container, text="刷新记录", state="disabled", command=self.controller.refresh_current_records)
        self.refresh_records_button.pack(side="left", padx=(0, 5))

        self.delete_button = ttk.Button(button_container, text="删除选中记录", state="disabled", command=self.controller.delete_selected_record)
        self.delete_button.pack(side="left")

        tree_frame = ttk.Frame(right_frame)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        columns = ("type", "name", "content", "proxied")
        self.records_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.records_tree.heading("type", text="类型"); self.records_tree.heading("name", text="名称")
        self.records_tree.heading("content", text="内容"); self.records_tree.heading("proxied", text="代理")
        self.records_tree.column("type", width=60, anchor="center"); self.records_tree.column("proxied", width=60, anchor="center")
        self.records_tree.grid(row=0, column=0, sticky="nsew")

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.records_tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        self.records_tree.config(yscrollcommand=tree_scrollbar.set)
        
        self.records_tree.bind("<<TreeviewSelect>>", self._on_record_selection_event)

        self._setup_styles()

    def _on_domain_select_event(self, event):
        selection_indices = self.domain_listbox.curselection()
        if not selection_indices: return
        self.controller.on_domain_selected(selection_indices[0])

    def _on_record_selection_event(self, event):
        selection_exists = bool(self.records_tree.selection())
        self.controller.on_record_selection_change(selection_exists)

    def get_selected_record_info(self):
        selected_ids = self.records_tree.selection()
        if not selected_ids: return None, None
        record_id = selected_ids[0]
        if record_id in ["empty", "error", "loading"]: return None, None
        item = self.records_tree.item(record_id)
        record_name = item['values'][1]
        return record_id, record_name

    def _setup_styles(self):
        # ... (此部分代码无变化)
        style = ttk.Style()
        style.theme_use('clam')
        bg_color, fg_color, select_bg = '#2b2b2b', '#d4d4d4', '#094771'
        entry_bg, s_trough, s_thumb, s_thumb_a = '#3c3f41', '#333333', '#4e4e4e', '#5f5f5f'
        style.configure('.', background=bg_color, foreground=fg_color, borderwidth=0, font=('sans-serif', 10))
        style.configure('TFrame', background=bg_color)
        style.configure('TButton', padding=6, relief='flat', background=entry_bg)
        style.map('TButton', background=[('active', '#4f5355'), ('disabled', '#333333')])
        style.configure('TLabel', background=bg_color)
        style.configure('Treeview', background='#333333', foreground=fg_color, fieldbackground='#333333', rowheight=28, borderwidth=0, relief='flat')
        style.map('Treeview', background=[('selected', select_bg)])
        style.configure('Treeview.Heading', background=entry_bg, font=('sans-serif', 10, 'bold'), relief='flat')
        style.configure("Vertical.TScrollbar", gripcount=0, background=s_thumb, darkcolor=entry_bg, lightcolor=entry_bg, troughcolor=s_trough, bordercolor=bg_color, relief='flat')
        style.map("Vertical.TScrollbar", background=[('active', s_thumb_a)])
        style.configure('TEntry', fieldbackground=entry_bg, foreground=fg_color, insertcolor=fg_color, borderwidth=1, relief='flat')
        style.map('TCombobox', fieldbackground=[('readonly', entry_bg)], selectbackground=[('readonly', select_bg)], foreground=[('readonly', fg_color)])
        self.root.option_add('*TCombobox*Listbox.background', entry_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', fg_color)
        self.root.option_add('*TCombobox*Listbox.selectBackground', select_bg)
        self.root.option_add('*TCombobox*Listbox.selectForeground', 'white')
        style.configure("Treeview", rowheight=28)
        self.records_tree.tag_configure(
            'special_message', 
            font=('sans-serif', 11, 'bold'), 
            foreground='#FFFFFF'
        )

    def set_record_buttons_state(self, active):
        state = "normal" if active else "disabled"
        self.add_button.config(state=state)
        self.refresh_records_button.config(state=state)
        # 删除按钮的状态由 set_delete_button_state 单独控制

    def set_delete_button_state(self, active):
        state = "normal" if active else "disabled"
        self.delete_button.config(state=state)

    def update_domain_list(self, zones, error):
        self.domain_listbox.delete(0, tk.END)
        if error:
            self.domain_listbox.insert(tk.END, f"加载失败: {error}")
            return
        if not zones:
             self.domain_listbox.insert(tk.END, "未找到任何域名")
             return
        for zone in zones:
            self.domain_listbox.insert(tk.END, zone['name'])

    def clear_ui(self):
        self.domain_listbox.delete(0, tk.END)
        self.clear_dns_records_list()
        self.set_record_buttons_state("disabled")

    def clear_dns_records_list(self):
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)

    def show_loading_records(self):
        self.clear_dns_records_list()
        self.records_tree.insert("", tk.END, values=("", "正在查询，请稍候...", "", ""), iid="loading", tags=('special_message',))

    def update_dns_records_list(self, records, error):
        self.clear_dns_records_list()
        if error:
            self.records_tree.insert("", tk.END, values=("错误", f"加载记录失败: {error}", "", ""), iid="error", tags=('special_message',))
            return
        if not records:
            self.records_tree.insert("", tk.END, values=("", "该域名下没有解析记录。", "", ""), iid="empty", tags=('special_message',))
            return
        for record in records:
            proxy_status = "是" if record.get('proxied', False) else "否"
            values = (record['type'], record['name'], record['content'], proxy_status)
            self.records_tree.insert("", tk.END, values=values, iid=record['id'])

    def set_status_message(self, text):
        self.status_label.config(text=text)