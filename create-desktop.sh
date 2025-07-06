#!/bin/bash

APP_DIR="$(pwd)"
SCRIPT_PATH="$APP_DIR/cli-manager.py"
LOCAL_PATH="$HOME/.local/share/applications/dns-manager.desktop"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"

mkdir -p "$(dirname "$LOCAL_PATH")"

cat > "$LOCAL_PATH" <<EOF
[Desktop Entry]
Encoding=UTF-8
Version=1.0
Type=Application
Exec=python3 $APP_DIR/main.py
Terminal=false
Name=dns-manager
Icon=$APP_DIR/cloudflare-dns-manager.png
Comment=cloudflare-dns-manager
GenericName=Internet Messenger
Name[zh_CN]=cloudflare-dns-manager
EOF

chmod +x "$LOCAL_PATH"
cp -f "$LOCAL_PATH" "$DESKTOP_DIR/dns-manager.desktop"
chmod +x "$DESKTOP_DIR/dns-manager.desktop"

if ! grep -Fxq "alias cli-manager='python3 \"$SCRIPT_PATH\"'" ~/.bashrc; then
    echo "alias cli-manager='python3 \"$SCRIPT_PATH\"'" >> ~/.bashrc
fi

echo "图标和别名已创建："
echo "$LOCAL_PATH"
echo "$DESKTOP_DIR/dns-manager.desktop"
echo "请执行 'source ~/.bashrc' 或重启终端以生效别名"
