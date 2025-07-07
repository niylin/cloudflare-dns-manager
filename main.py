# main.py
import argparse
import os
from app_controller import AppController

def main():
    parser = argparse.ArgumentParser(description="Cloudflare DNS Manager")
    parser.add_argument("--ui", choices=["tkinter", "gtk"], default="tkinter",
                        help="Specify the UI toolkit to use (tkinter or gtk)")
    args = parser.parse_args()

    if args.ui == "gtk":
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        
        app = Gtk.Application()
        controller = AppController(app, ui_type='gtk')
        app.run(None)

    else: # Default to tkinter
        import tkinter as tk
        
        root = tk.Tk()
        root.title("Cloudflare DNS Manager")

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, 'cloudflare-dns-manager.png')
            icon = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, icon)
        except tk.TclError:
            print(f"错误：无法从路径 '{icon_path}' 加载图标。")

        root.geometry("1200x700")
        root.config(bg='#2b2b2b')
        
        controller = AppController(root, ui_type='tkinter')
        root.mainloop()

if __name__ == "__main__":
    main()
