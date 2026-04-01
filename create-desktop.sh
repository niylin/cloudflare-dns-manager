#!/bin/bash

APP_DIR="$(pwd)"
LOCAL_PATH="$APP_DIR/cloudflare-dns-manager.desktop"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"

mkdir -p "$(dirname "$LOCAL_PATH")"

cat > "$LOCAL_PATH" <<EOF
[Desktop Entry]
Encoding=UTF-8
Version=1.0
Type=Application
Terminal=false
Name=Cloudflare DNS Manager
Comment=Manage your Cloudflare DNS records with a modern GTK 4 UI
Exec=python3 $APP_DIR/main.py 
Icon=$APP_DIR/img/cloudflare-dns-manager.png
Categories=Network;Utility;
StartupWMClass=org.niylin.cloudflare-dns-manager
Name[zh_CN]=Cloudflare DNS 管理器
EOF

cp -f "$LOCAL_PATH" "$DESKTOP_DIR/cloudflare-dns-manager.desktop"
chmod +x "$DESKTOP_DIR/cloudflare-dns-manager.desktop"


echo "图标已创建："
