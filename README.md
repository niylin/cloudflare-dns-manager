# Cloudflare Dns Manager
使用Cloudflare API来管理解析记录,适用于网络环境不佳,网页操作速度缓慢的场景

main.py 主入口,一个简单的GUI界面
cli-manager.py 在CLI中使用

## 密钥存储
使用 用户名,MAC,固定前缀 组合生成密钥对配置信息进行简单加密
存储在 $HOME/.config/cfconfig/cloudflare-dns-manager_hash.json

## 安装依赖
  
<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
 pip install requests colorama  
 sudo apt-get install python3-tk
  </code></pre>
</div>


## 使用方法  

<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
  # GUI
  git clone https://github.com/niylin/cloudflare-dns-manager.git
  cd cloudflare-dns-manager
  python3 main.py
  </code></pre>
</div>


<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
  # CLI
  git clone https://github.com/niylin/cloudflare-dns-manager.git
  cd cloudflare-dns-manager
  python3 cli-manager.py
  </code></pre>
</div>

### Linux创建桌面和应用菜单图标以及bash别名 "cli-manager"
<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
  cd cloudflare-dns-manager
  chmod +x create-desktop.sh
  ./create-desktop.sh
  </code></pre>
</div>

### 其他系统请手动创建

## 卸载,删除文件夹和图标即可
<div>
  <button class="btn" data-clipboard-target="#code"></button>
  <pre><code id="code" class="language-bash">
# 删除自动创建的内容
rm $HOME/.local/share/applications/dns-manager.desktop
rm $HOME/Desktop/dns-manager.desktop
rm -r $HOME/.config/cfconfig

  </code></pre>
</div>