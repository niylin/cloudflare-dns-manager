# main.py
import tkinter as tk
import os  
from app_controller import AppController

if __name__ == "__main__":
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

    controller = AppController(root)
    
    root.mainloop()